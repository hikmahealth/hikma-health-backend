import base64
import os

from flask.app import Flask

from hikmahealth.storage.adapters.base import IBaseStore
from hikmahealth.storage.adapters.gcp import GCPStore

import json

# name of the environment variable containing the
# selected blob store type
ENV_BLOB_STORE = "HH_STORAGE"


def _get_configuration_from_envrionment():
    """Initiates the selected by loading options from the environment variables"""
    store_type = os.environ.get(ENV_BLOB_STORE)

    assert (
        store_type is not None
    ), f"missing variable '{ENV_BLOB_STORE}' from the environment"

    if store_type == "gcp":
        from google.cloud import storage, exceptions
        from google.oauth2 import service_account

        bucket_name = os.environ.get("GCP_BUCKET_NAME", "hikmahealthdata.appspot.com")

        service_acc_details = os.environ["GCP_SERVICE_ACCOUNT_B64"]
        assert (
            service_acc_details is not None
        ), "missing GCP_SERVICE_ACCOUNT_B64 configuration"

        service_acc_details = json.loads(
            base64.b64decode(service_acc_details, validate=True)
        )
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

        assert bucket is not None, "failed to initiate bucket"

        # return "gcp", dict(bucket_name=bucket_name)
        return GCPStore(bucket)

    raise AssertionError(f"unknown store type '{store_type}'")


def get_storage() -> IBaseStore:
    return _get_configuration_from_envrionment()


def initialize_storage(app: Flask):
    # dry run to test if the storage configuration works
    # alternatively, might want to store this on app
    try:
        _get_configuration_from_envrionment()
    except:
        pass


# 1. source the configurations from database
# 2. checkout `firebase remote config`
