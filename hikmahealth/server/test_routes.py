import logging
import os
from flask import Blueprint, jsonify, request
from hikmahealth.storage.client import get_storage

log = logging.getLogger(__name__)
api = Blueprint("test-route", __name__)

# storage should allow uses to save files to the server
# to their target storages

@api.route("upload", methods=["PUT"])
def save_file_to_storage():
    print(request.files)
    store = get_storage()
    for ix, (name, f) in enumerate(request.files.items()):
        # print(f"{name}:", f)
        dotext = os.path.splitext(f.filename)[1].lower()
        store.put(f, f"{ix}-storage-111{dotext}", overwrite=True)

    log.info("testing something here")
    return jsonify(dict(ok=True)), 200
