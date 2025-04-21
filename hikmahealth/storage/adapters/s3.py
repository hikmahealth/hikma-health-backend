from hikmahealth.storage.adapters import base

"""Providing adapters and resource support S3-compatible storages"""

import dataclasses
from io import BytesIO

from hikmahealth.server.client.keeper import Keeper
from hikmahealth.storage.adapters.base import BaseAdapter


from hikmahealth.storage.objects import PutOutput

# List of supported S3 compatible hosts
STORE_HOST_TIGRISDATA = 'tigrisdata'
STORE_HOST_NATIVE = 'native'


# to include things like R2
def supported_s3_hosts():
    """Gets list of the S3-compatible storage currently supported"""
    return (STORE_HOST_TIGRISDATA,)


DEFAULT_BUCKET_NAME = 'hikmahealth-s3'
"""For the bucket configurations that allow this, this would be default bucket name that
is may be defaully created if the value was ever missing"""


@dataclasses.dataclass
class StoreConfig(base.BaseConfig):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str

    # depending of the type of S3 storage host, there might need to be specific types of configuraitons
    S3_COMPATIBLE_STORAGE_HOST: str

    # since this depends on the bucket_name being present or not
    # assuming this is native, this might also need to be optional
    AWS_ENDPOINT_URL_S3: str

    AWS_REGION: str = 'auto'

    # required to be defined if not using a
    # native S3 bucket
    S3_BUCKET_NAME: str | None = None

    @property
    def secret_fields(self):
        return ['AWS_SECRET_ACCESS_KEY', 'AWS_ACCESS_KEY_ID']


def initialize_store_config_from_keeper(kp: Keeper):
    # get variables
    config = dict()

    # print(StoreConfig.__dataclass_fields__)
    for v in StoreConfig.__dataclass_fields__.values():
        val = kp.get(v.name)
        if (
            v.default is dataclasses.MISSING
            and v.default_factory is dataclasses.MISSING
        ):
            assert val is not None and v.type is not None, (
                "missing required server variable '{}'".format(v.name)
            )

            assert isinstance(val, v.type), (
                "There's a type mismatch between code_value({}) != server_value({})".format(
                    v.type, type(val)
                )
            )

        config[v.name] = val

    return StoreConfig(**config)


UNIQUE_STORE_NAME = 's3'


class S3Store(BaseAdapter):
    def __init__(self, boto3_client, bucket_name: str, host: str):
        super().__init__(UNIQUE_STORE_NAME, f'{host}.202504.01')
        self.s3 = boto3_client
        self.bucket_name = bucket_name

    def download_as_bytes(self, name: str, *args, **kwargs) -> BytesIO:
        response = self.s3.get_object(
            Bucket=self.bucket_name, Key=name, ChecksumMode='ENABLED'
        )

        return BytesIO(response['Body'].read())

    def put(
        self, data: BytesIO, destination: str, mimetype: str | None = None, **kwargs
    ):
        assert isinstance(data, BytesIO), (
            'data argument needs to be a type `BytesIO`. instead got {}'.format(
                type(data)
            )
        )

        data.seek(0)
        response = self.s3.put_object(
            ACL='private',
            Bucket=self.bucket_name,
            Key=destination,
            ContentType=mimetype,
            Body=data.read(),
        )

        return PutOutput(uri=destination, hash=('md5', response['ETag']))
