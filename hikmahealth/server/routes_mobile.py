from io import BytesIO
import logging
import os
from uuid import uuid1
from boto3 import resource
from flask import Blueprint, request, Request, jsonify, abort, send_file
from psycopg import Connection
from psycopg.rows import dict_row

from hikmahealth.entity.sync import SyncToClient
from hikmahealth.server.client.keeper import get_keeper
from hikmahealth.server.client.resources import (
    ResourceManager,
    ResourceNotFound,
    ResourceStoreTypeMismatchError,
    get_resource_manager,
)
from hikmahealth.server.helpers import web as webhelper

from hikmahealth.server.api.auth import User
from hikmahealth.server.api import auth as auth
from hikmahealth.utils.errors import WebError

import time
from base64 import b64decode

from hikmahealth.utils.datetime import utc
from hikmahealth.server.client import db

from hikmahealth.entity import hh
from hikmahealth import sync

from datetime import datetime

from typing import Iterable
from collections import defaultdict
import traceback


api = Blueprint('api-mobile', __name__)
backcompatapi = Blueprint('api-mobile-backcompat', __name__, url_prefix='/api')


@backcompatapi.route('/login', methods=['POST'])
@api.route('/login', methods=['POST'])
def login():
    params = webhelper.assert_data_has_keys(request, {'email', 'password'})
    u = auth.get_user_from_email(params['email'], params['password'])
    return jsonify(u.to_dict())


@backcompatapi.route('/user/reset_password', methods=['POST'])
@api.route('/user/reset_password', methods=['POST'])
def reset_password():
    params = webhelper.assert_data_has_keys(
        request, {'email', 'password', 'new_password'}
    )
    u = auth.get_user_from_email(params['email'], params['password'])
    auth.reset_password(u, params['new_password'])
    return jsonify({
        'ok': True,
        'message': 'password updated',
    })


def _get_authenticated_user_from_request(request: Request) -> User:
    auth_header = request.headers.get('Authorization')
    encoded_username_password = auth_header.split(' ')[1]

    # Decode the username and password
    decoded_username_password = b64decode(encoded_username_password).decode()

    # Split the decoded string into email and password
    email, password = decoded_username_password.split(':')

    u = auth.get_user_from_email(email, password)
    return u


def _get_last_pulled_at_from(request: Request) -> datetime | None:
    """Uses the `last_pulled_at` part of the request query to return a `datetime.datetime` object"""
    last_pull_in_unix_time = request.args.get('last_pulled_at', None)

    if last_pull_in_unix_time is None:
        return None

    if type(last_pull_in_unix_time) == str:
        if str(last_pull_in_unix_time).isnumeric():
            # the from timestamp precision is in seconds as opposed to milliseconds (like in Js)
            # thus, you need to divide with 1000
            #
            # See this: https://stackoverflow.com/questions/10286224/javascript-timestamp-to-python-datetime-conversion
            return utc.from_unixtimestamp(last_pull_in_unix_time)

        try:
            # attempts to deal the date input as if it's a
            # ISO 8601 formatted date.
            return utc.from_iso8601(last_pull_in_unix_time)
        except Exception:
            traceback.format_exc()
            return None

    return None


# list of entities to get the diff from
ENTITIES_TO_PUSH_TO_MOBILE: dict[str, SyncToClient] = {
    'events': hh.Event,
    'patients': hh.Patient,
    'patient_additional_attributes': hh.PatientAttribute,
    'clinics': hh.Clinic,
    'visits': hh.Visit,
    'string_ids': hh.StringId,
    'string_content': hh.StringContent,
    'event_forms': hh.EventForm,
    'registration_forms': hh.PatientRegistrationForm,
    'appointments': hh.Appointment,
    'prescriptions': hh.Prescription,
}


@backcompatapi.route('/v2/sync', methods=['GET'])
@api.route('/sync', methods=['GET'])
def sync_v2_pull():
    _get_authenticated_user_from_request(request)
    last_synced_at = _get_last_pulled_at_from(request)
    schemaVersion = request.args.get('schemaVersion', None)
    migration = request.args.get('migration', None)

    if last_synced_at is None:
        raise WebError('missing last_pulled_at from request query', 400)

    changes_to_push_to_client = dict()

    with db.get_connection() as conn:
        for changekey, c in ENTITIES_TO_PUSH_TO_MOBILE.items():
            # getNthTimeSyncData
            # --------
            deltadata = c.get_delta_records(last_synced_at, conn)

            # if not deltadata.is_empty:
            # formatGETSyncResponse
            # --------
            changes_to_push_to_client[changekey] = deltadata.to_dict()

    # server generated timestamp for the current data changes
    timestamp = _get_timestamp_now()

    return jsonify({'changes': changes_to_push_to_client, 'timestamp': timestamp})


def _get_timestamp_now():
    return time.mktime(datetime.now().timetuple()) * 1000


# instantiates the manager to handle syncronization
# of changes to the databse
sink = sync.Sink[Connection]()

# queues the syncing operation and checks
# if the arguments are implement the right stuff
sink.add('patients', hh.Patient)
sink.add('patient_additional_attributes', hh.PatientAttribute)
sink.add('visits', hh.Visit)
sink.add('events', hh.Event)
sink.add('appointments', hh.Appointment)
sink.add('prescriptions', hh.Prescription)
# To make a new table syncable, be sure to include it here
# Ex.
#   class NewTableEntity:
#       def apply_delta_changes(deltadata, last_pushed_at, conn):
#           # sync logic here
#           pass
#
#   sink.add('<table_id>', NewTableEntity)


@backcompatapi.route('/v2/sync', methods=['POST'])
@api.route('/sync', methods=['POST'])
def sync_v2_push():
    # _get_authenticated_user_from_request(request)
    last_synced_at = _get_last_pulled_at_from(request)
    schemaVersion = request.args.get('schemaVersion', None)  # NOT USED
    migration = request.args.get('migration', None)  # NOT USED

    if last_synced_at is None:
        raise WebError('missing `last_pulled_at` from request query', 400)

    # expected body structure
    # { [s in 'events' | 'patients' | ....]: { "created": Array<dict[str, any]>, "updated": Array<dict[str, any]>, deleted: []str }}
    body = dict(request.get_json())

    with db.get_connection() as conn:
        try:
            for key, newdeltajson in body.items():
                # get the entity delta values
                deltadata = defaultdict(None, newdeltajson)

                # package delta data
                deltadata = sync.DeltaData(
                    created=deltadata.get('created'),
                    updated=deltadata.get('updated'),
                    # deleted=[{"id": id } for id in deltadata.get("deleted")] if deltadata.get("deleted") is not None else None,
                    deleted=deltadata.get('deleted'),
                )

                sink.push(key, deltadata, last_synced_at, conn)
            # after leaving the `with` context, there's an implied db.commit()
        except Exception as err:
            conn.close()
            print(err)
            print(traceback.format_exc())
            abort(500, description='An internal error occurred')

    return jsonify({'ok': True, 'timestamp': utc.now().isoformat()})


@api.route('/forms/resources', methods=['PUT'])
def put_resource_to_store():
    # # authenticating the
    _get_authenticated_user_from_request(request)
    # NOTE: might instead throw a WebError here
    rmgr = get_resource_manager()

    if rmgr is None:
        raise WebError('ResourceManager instance missing', status_code=412)

    resources = []
    for name, k in request.files.items():
        resources.append((
            BytesIO(k.stream.read()),
            lambda id: f'hh_forms_resources/{id}',
            k.mimetype,
        ))

    results = rmgr.put_resources(resources)

    return jsonify(data=[{'id': r['Id']} for r in results]), 201


@api.route('/forms/resources/<rid>', methods=['GET'])
def get_resource_from_store(rid: str):
    # # authenticating the
    _get_authenticated_user_from_request(request)
    rmgr = get_resource_manager()

    if rmgr is None:
        raise WebError('ResourceManager instance missing', status_code=412)

    try:
        result = rmgr.get_resource(rid)
        return send_file(result['Body'], download_name=rid, mimetype=result['Mimetype'])
    except (ResourceNotFound, ResourceStoreTypeMismatchError):
        return jsonify({'ok': False, 'message': 'Resource not found'}), 404


@api.errorhandler(500)
def internal_error(error):
    return jsonify({'ok': False, 'message': str(error.description)}), 500
