from dataclasses import dataclass
import dataclasses
from io import BytesIO
from google.cloud import storage

from hikmahealth.server.client.keeper import Keeper
from hikmahealth.storage.objects import PutOutput
from .base import BaseAdapter, BaseConfig


# NOTE: might change this into a usuful function
@dataclass
class StoreConfig(BaseConfig):
    GCP_SERVICE_ACCOUNT: dict
    GCP_BUCKET_NAME: str | None = None

    @property
    def secret_fields(self):
        return ['GCP_SERVICE_ACCOUNT']


# Default name of bucket expected to be in the GCP cloud storage
# if the variable is not defined, this default bucket name will be used
# instead
DEFAULT_GCP_BUCKET_NAME = 'hikmahealthdata.appspot.com'


def initialize_store_config_from_keeper(kp: Keeper):
    # get variables
    config = dict()

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


UNIQUE_STORE_NAME = 'gcp'
"""Name to uniquely identify the adapter associated with the storage"""


class GCPStore(BaseAdapter):
    """Adapter that makes storage possible on the Google Cloud Platform (GCP) Cloud Storage"""

    def __init__(self, bucket: storage.Bucket):
        super().__init__(UNIQUE_STORE_NAME, '202503.01')
        self.bucket = bucket

    def download_as_bytes(self, uri: str, *args, **kwargs) -> BytesIO:
        blob = self.bucket.blob(uri)
        return BytesIO(blob.download_as_bytes())

    def put(
        self,
        data: BytesIO,
        destination: str,
        mimetype: str | None = None,
        *args,
        **kwargs,
    ):
        """saves the data to a destination"""
        assert isinstance(data, BytesIO), (
            'data argument needs to be a type `BytesIO`. instead got {}'.format(
                type(data)
            )
        )

        # check if destination hasa a file
        blob = self.bucket.blob(destination)
        assert blob.name is not None, 'name is create from the bucket name'

        blob.upload_from_file(data, checksum='md5')

        # maybe us @dataclass later
        return PutOutput(uri=blob.name, hash=('md5', blob.md5_hash))
