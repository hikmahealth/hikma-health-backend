from .base import IBaseAdapter
from google.cloud import storage

class GCPStore(IBaseAdapter):
    """Adapter that makes storage possible on the Google Cloud Platform (GCP) Cloud Storage"""

    def __init__(self, client: storage.Client, bucket_name: str | None = None):
        self.bucket = client.bucket(bucket_name)
