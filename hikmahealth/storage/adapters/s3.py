"""Providing adapters and resource support S3-compatible storages"""

from io import BytesIO

from botocore.client import Config
from hikmahealth.storage.adapters.base import BaseAdapter
from dataclasses import dataclass

import asyncio
import boto3

from hikmahealth.storage.objects import PutOutput

# List of supported S3 compatible hosts
STORE_HOST_TIGRISDATA = 'tigrisdata'

DEFAULT_BUCKET_NAME = 'hikmahealth-s3'
"""For the bucket configurations that allow this, this would be default bucket name that
is may be defaully created if the value was ever missing"""

@dataclass
class S3Config:
    """Configuration needed to properly initialize the S3Store"""
    access_key_id: str
    secret_access_key: str

    # depending of the type of S3 storage host, there might need to be specific types of configuraitons
    store_host: str

    # since this depends on the bucket_name being present or not
    # assuming this is native, this might also need to be optional
    endpoint_url: str

    # required to be defined if not using a
    # native S3 bucket
    bucket_name: str

    region: str = 'auto'

    def __post_init__(self):
        if self.store_host == STORE_HOST_TIGRISDATA:
            assert self.endpoint_url is not None, f"since using '{STORE_HOST_TIGRISDATA}', endpoint also needs to be defined"
            assert self.bucket_name is not None,
            f"since using '{STORE_HOST_TIGRISDATA}', the bucket name needs to be pre-defined in the configuration"

        if self.bucket_name is None:
            self.bucket_name = DEFAULT_BUCKET_NAME






def create_client_from_config(config: S3Config):
    """Creates boto client from configuration describing the supported host"""
    session = boto3.Session(profile_name='hikmahealth')
    botoConfig = None

    if config.store_host == STORE_HOST_TIGRISDATA:
        botoConfig = Config(s3={'addressing_style': 'virtual'})

    # might want to create complete configuration
    # by using the boto3 client to make the rest of the parts that
    # are required

    svc = session.client(
        's3',
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        endpoint_url=config.endpoint_url,
        config=botoConfig,
    )

    return svc



class S3Store(BaseAdapter):
    def __init__(self, boto3_client, bucket_name: str):
        super().__init__('s3', 'tigrisdata.202504.01')
        self.s3 = boto3_client
        self.bucket_name = bucket_name

    def download_as_bytes(self, name: str) -> BytesIO:
        response = self.s3.get_object(
            Bucket=self.bucket_name,
            Key=name,
            ChecksumMode='ENABLED')

        return BytesIO(response["Body"].read())

    def put(self, data: BytesIO, destination: str, **opts):
        with BytesIO() as data:
            response = self.s3.put_object(
                Bucket=self.bucket_name,
                Key=destination,
                Body=data.read(),
                ChecksumAlgorithm="SHA256")

            return PutOutput(uri=destination, hash=('sha256', response["ChecksumSHA256"]))
