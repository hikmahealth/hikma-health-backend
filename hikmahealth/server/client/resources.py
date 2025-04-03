"""Resources client to manage relationship between the
resources that are created on the database and the information stored in the
respective stores"""

from dataclasses import dataclass

from io import BytesIO
from typing import Any, Callable, Iterable, Literal, Tuple
from uuid import UUID, uuid1

from botocore.client import ClientError
from flask.app import Flask
from psycopg.rows import dict_row

from hikmahealth.server.client import db
from hikmahealth.storage.adapters.base import BaseAdapter


from .keeper import Keeper

import datetime

# storege type
STORE_TYPE_AWS = 'aws'
STORE_TYPE_GCP = 'gcp'


def get_supported_stores():
    return (STORE_TYPE_GCP, STORE_TYPE_AWS)


@dataclass
class ResourceConfig:
    store_type: str
    # store_version: str

    # values are stored here when any resource is stored
    last_used_store_type: str | None = None
    last_used_version: str | None = None
    last_used_timestamp: datetime.datetime | None = None


def initialize_config_from_keeper(kp: Keeper):
    config_dict = dict()

    # NOTE, these are 3 separate pq calls
    config_dict['store_type'] = kp.get('HH_STORE_TYPE')
    # config_dict['store_version'] = kp.get('HH_STORE_VERSION')

    d = kp.get_as_json('HH_STORE_LAST_USED')
    if d is not None:
        config_dict['last_used_store_type'] = d['type']
        config_dict['last_used_version'] = d['type']
        config_dict['last_used_timestamp'] = datetime.datetime.fromtimestamp(
            int(d['type']), tz=datetime.UTC
        )

    return ResourceConfig(**config_dict)


class ResourceManager:
    """Manages fetching and getting resources"""

    def __init__(self, kp: Keeper):
        self._keeper = kp
        self.store: BaseAdapter | None = None

        config = initialize_config_from_keeper(kp)

        if config.store_type == STORE_TYPE_GCP:
            from google.cloud import storage, exceptions
            from google.oauth2 import service_account

            from hikmahealth.storage.adapters import gcp

            gcpconfig = gcp.initialize_store_config_from_keeper(kp)

            service_acc_details = gcpconfig.GCP_SERVICE_ACCOUNT
            bucket_name = gcpconfig.GCP_BUCKET_NAME

            if bucket_name is None:
                bucket_name = gcp.DEFAULT_GCP_BUCKET_NAME

            credentials = service_account.Credentials.from_service_account_info(
                service_acc_details
            )
            client = storage.Client(credentials=credentials)

            # check if bucket exists
            bucket: storage.Bucket | None = None
            try:
                bucket = client.get_bucket(bucket_name)
            except exceptions.NotFound:
                bucket = client.create_bucket(bucket_name)

            assert bucket is not None, 'failed to initiate bucket'

            # TODO: save config with possibly new applied settings
            # gcp.update_store_config_to_keeper(kp, s3config)

            self.store = gcp.GCPStore(bucket)

        if config.store_type == STORE_TYPE_AWS:
            import boto3
            from botocore.client import Config

            from hikmahealth.storage.adapters import s3 as s3

            s3config = s3.initialize_store_config_from_keeper(kp)
            session = boto3.Session()
            botoConfig = None

            bucket_name = s3config.S3_BUCKET_NAME

            if s3config.S3_COMPATIBLE_STORAGE_HOST == s3.STORE_HOST_TIGRISDATA:
                # for tigris, because of it's virtual pathing,
                #  `bucket_name` needs to be pre-defined
                assert bucket_name is not None, (
                    'since using {}, `bucket_name` needs to be explicitly defined'.format(
                        s3config.S3_COMPATIBLE_STORAGE_HOST
                    )
                )

                botoConfig = Config(s3={'addressing_style': 'virtual'})

            svc = session.client(
                's3',
                aws_access_key_id=s3config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=s3config.AWS_SECRET_ACCESS_KEY,
                endpoint_url=s3config.AWS_ENDPOINT_URL_S3,
                config=botoConfig,
            )

            if bucket_name is None or bucket_name == s3.DEFAULT_BUCKET_NAME:
                # attempt to make bucket with name
                bucket_name = s3.DEFAULT_BUCKET_NAME
                try:
                    svc.head_bucket(Bucket=bucket_name)
                    # if this doesn't throw, then the bucket exists
                except ClientError as e:
                    error_code = int(e.response['Error']['Code'])
                    if error_code == 404:
                        svc.create_bucket(Bucket=bucket_name, ACL='private')

                # if exists, will through error

                # update config
                s3config.S3_BUCKET_NAME = bucket_name

            # TODO: save config with possibly new applied settings
            # s3.update_store_config_to_keeper(kp, s3config)

            assert bucket_name is not None, 'bucket_name is still not set'

            self.store = s3.S3Store(
                svc, bucket_name, s3config.S3_COMPATIBLE_STORAGE_HOST
            )

        assert self.store is not None, (
            f"failed to initiate storage. unknown store type '{config.store_type}'"
        )

    def get_resource(self, id: str):
        data = None
        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT store, store_version, uri, mimetype FROM resources
                    WHERE id = %s::uuid LIMIT 1;
                    """,
                    (id,),
                )

                data = cur.fetchone()

        if data is None:
            raise ResourceNotFound(
                "unable to find resource with variable '{}'".format(id)
            )

        if data['store'] != self.store.NAME:
            raise ResourceStoreTypeMismatch()

        mem = self.store.download_as_bytes(data['uri'])
        return dict(Body=mem, Mimetype=data['mimetype'])

    def put_resources(
        self, resources: Iterable[Tuple[BytesIO, str | Callable[[UUID], str], str]]
    ):
        resources_data = list()
        for b, destination, mimetype in resources:
            resourceid = uuid1()  # id is managed by the resource manager

            if callable(destination):
                d = destination(resourceid)
            else:
                d = destination

            out = self.store.put(
                b,
                d,
                overwrite=True,
            )

            resources_data.append(
                dict(
                    Id=resourceid,
                    Uri=out.uri,
                    Checksum=':'.join(out.hash),
                    Mimetype=mimetype,
                )
            )

        try:
            with db.get_connection() as conn:
                for d in resources_data:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO resources
                                (id, store, store_version, uri, hash, mimetype)
                            VALUES
                                (%s::uuid, %s, %s, %s, %s, %s)
                            """,
                            [
                                d['Id'],
                                self.store.NAME,
                                self.store.VERSION,
                                d['Uri'],
                                d['Checksum'],
                                d['Mimetype'],
                            ],
                        )

            return resources_data

        except Exception as err:
            raise ResourceOperationError(
                '[store: {}] failed to store resource at destinations {}. {}',
                store.NAME,
                ','.join([d[1] for d in resources]),
                err,
            )


class ResourceStoreTypeMismatch(Exception):
    """Error thrown when the `store_type` of the resource stored, doesn't match
    with the currently set resource store type."""

    pass


class ResourceOperationError(Exception):
    """Generic error when there's an issue when making a `Resources` related operation"""

    pass


class ResourceNotFound(Exception):
    """Error thrown when there isn't a resource on a `get_resource` attempt"""

    pass


def initialize_storage(app: Flask):
    # TODO: implement handling of availability of `ResourceManager` form here
    pass
