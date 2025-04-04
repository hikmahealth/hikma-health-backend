from collections import defaultdict
import logging
import os
from flask import Blueprint, jsonify, request
from hikmahealth.server.client.keeper import get_keeper
from hikmahealth.server.client.resources import initialize_resource_manager

log = logging.getLogger(__name__)
api = Blueprint('test-route', __name__)


@api.route('env', methods=['POST', 'GET'])
def test_keeper_vals():
    kp = get_keeper()
    if request.method.lower() == 'post':
        l = request.get_json()
        if l is not None:
            for j in l:
                d = defaultdict(lambda: None, j)
                key = d['key']
                if key is None:
                    return jsonify(
                        dict(ok=False, message=f'missing argument key in {d}')
                    ), 400

                if 'json' in d:
                    kp.set_json(key, d.get('json'))
                else:
                    kp.set_str(key, d.get('value'))

        # everytime we update the env, we should also re-initialize the resource manager
        initialize_resource_manager()

        return jsonify(dict(ok=True)), 201

    output = dict()
    for k in request.args.getlist('key'):
        output[k] = kp.get(k)

    for k in request.args.getlist('key_json'):
        output[k] = kp.get_as_json(k)

    return jsonify(dict(values=output)), 200
