from collections.abc import Iterable
from flask import Blueprint, jsonify, request

from hikmahealth.server.api import middleware
from hikmahealth.server.client.keeper import get_keeper
from hikmahealth.server.client.resources import get_config_from_keeper
from hikmahealth.utils.errors import WebError
from hikmahealth.utils.textparse import parse_config

api = Blueprint('api-admin-storage', __name__)


@api.get('/storage')
@middleware.authenticated_admin
def get_storage_configuration():
    config = get_config_from_keeper(get_keeper())
    if config is None:
        return jsonify(
            is_configured=False,
        ), 200

    return jsonify(is_configured=True, store=config.store_type), 200


# Current implementation should work for any storage
@api.post('/')
@middleware.authenticated_admin
def set_storage_configuration():
    keeper = get_keeper()
    if request.content_type == 'application/json':
        # will extract information as JSON `Array<{ key: string } & ({ value: string } | { json: string })>`
        var_data = request.get_json(force=True)

        if isinstance(var_data, Iterable) and not isinstance(var_data, (str, bytes)):
            for d in var_data:
                if not isinstance(d, dict):
                    raise WebError('invalid value at {}'.format(d))

                entry_key = d.get('key')
                if entry_key is None:
                    raise WebError("missing 'key' at:\n {}".format(d))

                if 'value' in d:
                    keeper.set_str(d['key'], d['value'])
                elif 'json' in d:
                    keeper.set_json(d['key'], d['json'])
                else:
                    raise WebError(
                        'expected other value to include either `value|json`. See {}'.format(
                            d
                        )
                    )

        else:
            raise WebError('invalid data shape')

    if request.content_type == 'text/plain':
        # will extract the information as if it were a .env file
        var_map = parse_config(request.get_data(as_text=True))

        for key, value in var_map.items():
            keeper.set_str(key, value)

    return jsonify(ok=True), 201
