import os

from google.cloud import storage

from hikmahealth.storage.adapters.gcp import GCPStore

# name of the environment variable containing the
# selected blob store type
ENV_BLOB_STORE = "HH_STORAGE"

def create_store_from_environment():
    """Initiates the selected by loading options from the environment variables"""
    store_type = os.environ.get(ENV_BLOB_STORE)

    assert store_type is not None, f"missing variable '{ENV_BLOB_STORE}' from the environment"

    if store_type == "gcp":
        bucket_name = os.environ.get("GCP_BUCKET_NAME", 'hikmahealthdata')
        return GCPStore(storage.Client(), bucket_name)

    raise AssertionError(f"unknown store type '{store_type}'")
