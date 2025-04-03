from io import BytesIO
from google.cloud import storage
from werkzeug.datastructures import FileStorage

from hikmahealth.storage.objects import PutOutput
from .base import BaseAdapter

# TODO: have a resources table
# Abstract away the storage information


class GCPStore(BaseAdapter):
    """Adapter that makes storage possible on the Google Cloud Platform (GCP) Cloud Storage"""

    def __init__(self, bucket: storage.Bucket):
        super().__init__('gcp', '202503.01')
        self.bucket = bucket

    def download_as_bytes(self, uri: str) -> BytesIO:
        blob = self.bucket.blob(uri)
        return BytesIO(blob.download_as_bytes())

    def put(self, data: BytesIO, destination: str, mimetype: str | None = None):
        """saves the data to a destination"""
        assert isinstance(data, BytesIO), 'data argument needs to be a type `BytesIO`'

        # check if destination hasa a file
        blob = self.bucket.blob(destination)
        assert blob.name is not None, 'name is create from the bucket name'

        blob.upload_from_file(data, checksum='md5')

        # maybe us @dataclass later
        return PutOutput(uri=blob.name, hash=('md5', blob.md5_hash))
