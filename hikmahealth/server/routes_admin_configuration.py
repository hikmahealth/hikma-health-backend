from hikmahealth.server.client.resources import VAR_STORE_TYPE
from hikmahealth.server.client.resources import get_supported_stores
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
def get_storage_configuration(_):
    config = get_config_from_keeper(get_keeper())
    if config is None:
        return jsonify(
            is_configured=False,
        ), 200

    keeper = get_keeper()

    if config.store_type == 's3':
        from hikmahealth.storage.adapters import s3

        try:
            data = s3.initialize_store_config_from_keeper(keeper)
            print('S# data:', data.to_dict(ignore_nil=True))
            return jsonify(
                is_configured=True,
                store=config.store_type,
                keys=[
                    dict(key=VAR_STORE_TYPE, value=config.store_type),
                    *_dict_to_entries((data.to_dict(ignore_nil=True))),
                ],
            ), 200
        except Exception as err:
            raise WebError(
                'invalid S3 configuration. {}'.format(','.join(err.args)),
                status_code=400,
            )

    if config.store_type == 'gcp':
        from hikmahealth.storage.adapters import gcp

        try:
            data = gcp.initialize_store_config_from_keeper(keeper)
            return jsonify(
                is_configured=True,
                store=config.store_type,
                keys=[
                    dict(key=VAR_STORE_TYPE, value=config.store_type),
                    *_dict_to_entries((data.to_dict(ignore_nil=True))),
                ],
            ), 200
        except Exception as err:
            raise WebError(
                'invalid GCP configuration. {}'.format(','.join(err.args)),
                status_code=400,
            )

    raise WebError(
        'missing configuration for {}'.format(config.store_type),
        status_code=500,
    )


def _dict_to_entries(d: dict):
    return [{'key': key, 'value': value} for key, value in d.items()]


@api.get('/storage/<store_type>')
@middleware.authenticated_admin
def get_store_configuration_value(_, store_type: str):
    if store_type not in get_supported_stores():
        raise WebError(
            "unknown or unsupported store type '{}'. currently only supporting '{}'",
            store_type,
            ', '.join(get_supported_stores()),
        )

    keeper = get_keeper()

    if store_type == 's3':
        from hikmahealth.storage.adapters import s3

        try:
            data = s3.initialize_store_config_from_keeper(keeper)
            return jsonify(_dict_to_entries(data.to_dict(ignore_nil=True))), 200
        except Exception as err:
            raise WebError(
                'invalid S3 configuration. {}'.format(','.join(err.args)),
                status_code=400,
            )

    if store_type == 'gcp':
        from hikmahealth.storage.adapters import gcp

        try:
            data = gcp.initialize_store_config_from_keeper(keeper)
            return jsonify(_dict_to_entries(data.to_dict(ignore_nil=True))), 200
        except Exception as err:
            raise WebError(
                'invalid GCP configuration. {}'.format(','.join(err.args)),
                status_code=400,
            )


@api.get('/storage/<store_type>/validate')
@middleware.authenticated_admin
def validate_storage_configuration(_, store_type: str):
    """Validate if the configurations is properly set, according to the chosen storage type"""
    if store_type not in get_supported_stores():
        raise WebError(
            "unknown or unsupported store type '{}'. currently only supporting '{}'",
            store_type,
            ', '.join(get_supported_stores()),
        )

    keeper = get_keeper()

    if store_type == 's3':
        from hikmahealth.storage.adapters import s3

        try:
            data = s3.initialize_store_config_from_keeper(keeper)
            print(data)
            return jsonify(valid=True), 200
        except Exception as err:
            raise WebError(
                'invalid S3 configuration. {}'.format(','.join(err.args)),
                status_code=400,
            )

    if store_type == 'gcp':
        from hikmahealth.storage.adapters import gcp

        try:
            data = gcp.initialize_store_config_from_keeper(keeper)
            print(data)
            return jsonify(valid=True), 200
        except Exception as err:
            raise WebError(
                'invalid GCP configuration. {}'.format(','.join(err.args)),
                status_code=400,
            )

    raise Exception(
        "could not check for configuration of store type '{}'".format(store_type)
    )


# Current implementation should work for any storage
@api.post('/')
@middleware.authenticated_admin
def set_storage_configuration(_):
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
