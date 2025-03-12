from google.cloud import storage
from werkzeug.datastructures import FileStorage
from .base import IBaseStore


class GCPStore(IBaseStore):
    """Adapter that makes storage possible on the Google Cloud Platform (GCP) Cloud Storage"""

    def __init__(self, bucket: storage.Bucket):
        # create if bucket doesn't exist
        self.bucket = bucket

    def get(self, name: str):
        pass


    def put(self, data: FileStorage, destination: str, **kwargs):
        """saves the data to a destination"""
        # check if destination hasa a file
        blob = self.bucket.blob(destination)
        blob.upload_from_file(data)
        print("gcp storage done")
