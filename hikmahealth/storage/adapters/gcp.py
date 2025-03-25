from io import BytesIO
from google.cloud import storage
from werkzeug.datastructures import FileStorage
from .base import BaseAdapter

# TODO: have a resources table
# Abstract away the storage information


class GCPStore(BaseAdapter):
    """Adapter that makes storage possible on the Google Cloud Platform (GCP) Cloud Storage"""

    def __init__(self, bucket: storage.Bucket):
        super().__init__('gcp', '202503.01')
        self.bucket = bucket

    def download_as_bytes(self, uri: str):
        blob = self.bucket.blob(uri)
        return blob.download_as_bytes()

    def put(
        self, data: BytesIO, destination: str, mimetype: str | None = None, **kwargs
    ):
        """saves the data to a destination"""
        # check if destination hasa a file
        blob = self.bucket.blob(destination)
        blob.upload_from_file(data, checksum='md5')

        # maybe us @dataclass later
        return dict(uri=blob.name, md5_hash=blob.md5_hash)
