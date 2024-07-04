
from flask import Blueprint, request, Request, jsonify

from hikmahealth.server.helpers import web

from hikmahealth.server.api.user import User
from hikmahealth.server.api import user as userapi

import time
from base64 import b64decode

import hikmahealth.utils.datetime as dateutils
from hikmahealth.server.client import db

from hikmahealth.entity import concept, sync
from datetime import timezone, datetime


api = Blueprint('api-mobile', __name__)


@api.route('/login', methods=['POST'])
def login():
    params = web.assert_data_has_keys(request, {"email", "password"})
    u = userapi.authenticate_with_email(params["email"], params["password"])
    return jsonify(u.to_dict())


@api.route('/user/reset_password', methods=['POST'])
def reset_password():
    params = web.assert_data_has_keys(request, {"email", "password", "new_password"})
    u = userapi.authenticate_with_email(params["email"], params["password"])    
    userapi.reset_password(u, params['new_password'])
    return jsonify(u.to_dict())


def _get_authenticated_user_from_request(request: Request) -> User:
    auth_header = request.headers.get('Authorization')
    encoded_username_password = auth_header.split(' ')[1]

    # Decode the username and password
    decoded_username_password = b64decode(encoded_username_password).decode()

    # Split the decoded string into email and password
    email, password = decoded_username_password.split(':')

    u = userapi.authenticate_with_email(email, password)
    return u


def _get_last_pulled_at_from(request: Request) -> int | str:
    lastPulledAtReq = request.args.get("last_pulled_at", 0)
    lastPulledAt = (
        int(lastPulledAtReq)
        if type(lastPulledAtReq) == int
        or type(lastPulledAtReq) == float
        or (type(lastPulledAtReq) == str and str(lastPulledAtReq).isnumeric())
        else 0
    )

    ms = datetime.now()
    syncTimestamp = time.mktime(ms.timetuple()) * 1000

    print(
        f"lastPulledAt: {lastPulledAt} ({lastPulledAtReq}) and server says: {syncTimestamp} and a difference of: {int(lastPulledAt or 0) - syncTimestamp}"
    )

    print(f"body: {request}")
    return lastPulledAtReq

@api.route('/sync', methods=['GET'])
def sync_v2_pull():
    _get_authenticated_user_from_request(request)
    last_synced_at = _get_last_pulled_at_from(request)
    schemaVersion = request.args.get("schemaVersion", None)
    migration = request.args.get("migration", None)

    
    # list of entities to get the diff from
    entities_to_sync: dict[str, sync.SyncDownEntity] = {
        "events": concept.Event,
        "patients": concept.Patient,
        "visits": concept.Visit,
    }

    
    changes_to_push_to_client = dict()

    with db.get_connection() as conn:
        for changekey, c in entities_to_sync.items():
            # getNthTimeSyncData
            # --------
            deltadata = c.get_delta_records(last_synced_at, conn)

            # formatGETSyncResponse
            # --------
            changes_to_push_to_client[changekey] = deltadata.to_dict()

    return jsonify({
        "changes": changes_to_push_to_client,
        "timestamp": _get_timestamp_now()
    })


_KNOWN_ENTITIES_TO_SYNC_UP: dict[str, sync.ISyncUp] = {
    "events": concept.Event,
    "patients": concept.Patient 
}

@api.route('/sync', methods=['POST'])
def sync_v2_push():
    _get_authenticated_user_from_request(request)
    last_synced_at = _get_last_pulled_at_from(request)
    schemaVersion = request.args.get("schemaVersion", None)
    migration = request.args.get("migration", None)

    # 2. If the changes object contains a record that has been modified on the server after lastPulledAt, you MUST abort push and return an error code
    
    # expected body structure
    # { [s in 'events' | 'patients' | ....]: { "created": Array<dict[str, any]>, "updated": Array<dict[str, any]>, deleted: []str }}
    body = dict(request.get_json())

    try:
        for entitykey, deltadata in body:
            if entitykey not in _KNOWN_ENTITIES_TO_SYNC_UP:
                continue

            e = _KNOWN_ENTITIES_TO_SYNC_UP[entitykey]

            # package delta data
            deltadata = sync.DeltaData(
                created=deltadata["created"],
                updated=deltadata["updated"],
                deleted=[{"id": id} for id in deltadata["deleted"]] if deltadata["deleted"] is not None else None
            )

            e.apply_delta_changes(deltadata, last_pushed_at=last_synced_at, conn=db.get_connection())

        return jsonify({ "ok": True })    
    except Exception as err:
        print(err)
        return jsonify({ "ok": False, "message": "failed horribly" })
    

def _get_timestamp_now():
    return time.mktime(datetime.now().timetuple()) * 1000