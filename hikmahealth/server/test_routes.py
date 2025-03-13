import logging
import os
from flask import Blueprint, jsonify, request
from hikmahealth.keeper import get_keeper
from hikmahealth.storage.client import get_storage

log = logging.getLogger(__name__)
api = Blueprint('test-route', __name__)

# storage should allow uses to save files to the server
# to their target storages


@api.route('upload', methods=['PUT'])
def save_file_to_storage():
    print(request.files)
    store = get_storage()
    for ix, (name, f) in enumerate(request.files.items()):
        # print(f"{name}:", f)
        dotext = os.path.splitext(f.filename)[1].lower()
        store.put(f, f'{ix}-storage-111{dotext}', overwrite=True)

    return jsonify(dict(ok=True)), 200


@api.route('env', methods=['POST', 'GET'])
def test_keeper_vals():
    kp = get_keeper()
    if request.method.lower() == 'post':
        j = request.json
        if j is not None:
            for d in j:
                kp.set_str(d['key'], d['value'])

        return jsonify(dict(ok=True)), 201

    output = dict()
    for k in request.args.getlist('key'):
        output[k] = kp.get(k)

    return jsonify(dict(values=output)), 200
