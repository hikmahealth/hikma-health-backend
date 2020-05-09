import os
from typing import Optional

from google.cloud import storage
from google.api_core.exceptions import NotFound
from werkzeug.datastructures import FileStorage

from config import LOCAL_PHOTO_STORAGE_DIR, PHOTOS_STORAGE_BUCKET, STORAGE_BACKEND

if STORAGE_BACKEND == 'gcs':
    storage_client = storage.Client()


def store_photo(file_storage: FileStorage) -> str:
    base_name = file_storage.filename
    local_filename = os.path.join(LOCAL_PHOTO_STORAGE_DIR, base_name)
    with open(local_filename, 'wb') as handle:
        file_storage.save(handle)

    if STORAGE_BACKEND == 'gcs':
        bucket = storage_client.bucket(PHOTOS_STORAGE_BUCKET)
        blob = bucket.blob(base_name)
        print(f'Uploading {base_name} to GCS bucket {PHOTOS_STORAGE_BUCKET}...')
        blob.upload_from_filename(local_filename)
    return base_name


def retrieve_photo(base_filename: str) -> Optional[str]:
    local_filename = os.path.join(LOCAL_PHOTO_STORAGE_DIR, base_filename)
    if os.path.exists(local_filename):
        return local_filename
    else:
        return _retrieve_photo_from_gcs(base_filename)


def _retrieve_photo_from_gcs(base_filename: str) -> Optional[str]:
    bucket = storage_client.bucket(PHOTOS_STORAGE_BUCKET)
    blob = bucket.blob(base_filename)
    local_filename = os.path.join(LOCAL_PHOTO_STORAGE_DIR, base_filename)
    try:
        blob.download_to_filename(local_filename)
        return local_filename
    except NotFound:
        return None
