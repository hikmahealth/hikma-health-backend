import base64
import os

from flask.app import Flask
from sqlalchemy.pool.impl import AssertionPool

from hikmahealth.keeper import Keeper
from hikmahealth.storage.adapters.base import BaseAdapter
from hikmahealth.storage.adapters.gcp import GCPStore

import json

from hikmahealth.storage.errors import UnsupportedStoreError

# types of supported storages
STORE_TYPE_GCP = 'gcp'


def create_instance(store_type: str, **opts):
    """Creates an instance for the storage using configuration that are passed on the function"""
    if store_type == STORE_TYPE_GCP:
        from google.cloud import storage, exceptions
        from google.oauth2 import service_account

        service_acc_details = opts['gcp_service_account']
        bucket_name = opts['bucket_name']
        assert isinstance(bucket_name, str), (
            "missing 'bucket_name' in kwargs or is not string"
        )
        assert service_acc_details is not None, (
            "missing 'gcp_service_account' in kwargs"
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

        assert bucket is not None, 'failed to initiate bucket'

        return GCPStore(bucket)

    raise UnsupportedStoreError()


# name of the environment variable containing the
# selected blob store type
ENV_BLOB_STORE = 'HH_STORE_TYPE'

# Default name of bucket expected to be in the GCP cloud storage
# if the variable is not defined, this default bucket name will be used
# instead
DEFAULT_GCP_BUCKET_NAME = 'hikmahealthdata.appspot.com'


def _load_configuration_from_envrionment():
    """Constructs the storage configuration from values in the environment variables"""
    store_type = os.environ.get(ENV_BLOB_STORE)

    assert store_type is not None, (
        f"missing variable '{ENV_BLOB_STORE}' from the environment"
    )

    if store_type == 'gcp':
        bucket_name = os.environ.get('GCP_BUCKET_NAME', DEFAULT_GCP_BUCKET_NAME)
        service_acc_details = os.environ['GCP_SERVICE_ACCOUNT_B64']
        assert service_acc_details is not None, (
            'missing GCP_SERVICE_ACCOUNT_B64 from environment variables'
        )

        service_acc_details = json.loads(
            base64.b64decode(service_acc_details, validate=True)
        )

        return dict(
            store_type='gcp',
            bucket_name=bucket_name,
            gcp_service_account=service_acc_details,
        )

    raise AssertionError('currently supported configuration is `gcp`')


# values are stored as server variables containing the type of storage
# to be configured with the server
SERVAR_STORE_TYPE = ENV_BLOB_STORE


def _load_configuration_from_keeper(kp: Keeper):
    store_type = kp.get(SERVAR_STORE_TYPE)

    assert store_type is not None, f"missing server variable '{SERVAR_STORE_TYPE}'"

    if store_type == 'gcp':
        bucket_name = kp.get('GCP_BUCKET_NAME')
        if bucket_name is None:
            kp.set_str('GCP_BUCKET_NAME', DEFAULT_GCP_BUCKET_NAME)
            bucket_name = DEFAULT_GCP_BUCKET_NAME

        service_acc_details = kp.get_as_json('GCP_SERVICE_ACCOUNT')
        assert service_acc_details is not None, (
            "missing 'GCP_SERVICE_ACCOUNT' required parameter for GCP store."
        )

        return dict(
            store_type='gcp',
            bucket_name=bucket_name,
            gcp_service_account=service_acc_details,
        )

    raise AssertionError(
        'server variable not containing the supported storages [`gcp`]'
    )


def get_storage():
    # return create_instance(**_load_configuration_from_envrionment())
    return create_instance(**_load_configuration_from_keeper(Keeper()))


def initialize_storage(app: Flask):
    # dry run to test if the storage configuration works
    # alternatively, might want to store this on app
    try:
        # dry run
        get_storage()
    except:
        pass


# 1. source the configurations from database
# 2. checkout `firebase remote config`
