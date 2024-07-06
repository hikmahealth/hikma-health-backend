
from flask import Blueprint, request, Request, jsonify

from hikmahealth.server.helpers import web as webhelper

from hikmahealth.server.api.auth import User
from hikmahealth.server.api import auth as auth
from hikmahealth.utils.errors import WebError

import time
from base64 import b64decode

from hikmahealth.utils import datetime as dateutils
from hikmahealth.server.client import db

from hikmahealth.entity import concept, sync
from datetime import timezone, datetime

from typing import Iterable
from collections import defaultdict
import traceback

api = Blueprint('api-mobile', __name__)
backcompatapi = Blueprint('api-mobile-backcompat', __name__, url_prefix="/api")


@backcompatapi.route('/login', methods=['POST'])
@api.route('/login', methods=['POST'])
def login():
    params = webhelper.assert_data_has_keys(request, {"email", "password"})
    u = auth.authenticate_with_email(params["email"], params["password"])
    return jsonify(u.to_dict())


@backcompatapi.route('/user/reset_password', methods=['POST'])
@api.route('/user/reset_password', methods=['POST'])
def reset_password():
    params = webhelper.assert_data_has_keys(request, {"email", "password", "new_password"})
    u = auth.authenticate_with_email(params["email"], params["password"])    
    auth.reset_password(u, params['new_password'])
    return jsonify(u.to_dict())


def _get_authenticated_user_from_request(request: Request) -> User:
    auth_header = request.headers.get('Authorization')
    encoded_username_password = auth_header.split(' ')[1]

    # Decode the username and password
    decoded_username_password = b64decode(encoded_username_password).decode()

    # Split the decoded string into email and password
    email, password = decoded_username_password.split(':')

    u = auth.authenticate_with_email(email, password)
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
    syncTimestamp = time.mktime(ms.timetuple())

    print(
        f"lastPulledAt: {lastPulledAt} ({lastPulledAtReq}) and server says: {syncTimestamp} and a difference of: {int(lastPulledAt or 0) - syncTimestamp}"
    )

    print(f"body: {request}")
    return int(lastPulledAt) / 1000


@backcompatapi.route("/sync", methods=["POST"])
def sync():
    params = webhelper.assert_data_has_keys(request, {"email", "password"}, data_type="form")
    User.authenticate(params["email"], params["password"])
    if "db" not in request.files:
        raise WebError("db must be provided", 400)

    synchronizer = DbSynchronizer(request.files["db"])
    if not synchronizer.prepare_sync():
        raise WebError("Synchronization failed", 500)

    synchronizer.execute_server_side_sql()
    return jsonify({"to_execute": synchronizer.get_client_sql()})

@backcompatapi.route('/v2/sync', methods=['GET'])
@api.route('/sync', methods=['GET'])
def sync_v2_pull():
    # _get_authenticated_user_from_request(request)
    last_synced_at = _get_last_pulled_at_from(request)
    schemaVersion = request.args.get("schemaVersion", None)
    migration = request.args.get("migration", None)

    
    # list of entities to get the diff from
    entities_to_sync: dict[str, sync.SyncDownEntity] = {
        "events": concept.Event,
        "patients": concept.Patient,
        "visits": concept.Visit,
        # "nurses": concept.Nurse,
    }

    changes_to_push_to_client = dict()

    with db.get_connection() as conn:
        for changekey, c in entities_to_sync.items():
            # getNthTimeSyncData
            # --------
            deltadata = c.get_delta_records(last_synced_at, conn)

            # if not deltadata.is_empty:
            # formatGETSyncResponse
            # --------
            changes_to_push_to_client[changekey] = deltadata.to_dict()

    return jsonify({
        "changes": changes_to_push_to_client,
        "timestamp": _get_timestamp_now()
    })


# make sure to observe order for how the tables are created
_KNOWN_ENTITIES_TO_SYNC_UP: Iterable[tuple[str, sync.ISyncUp]] = (
    ("patients", concept.Patient),
    # ("patient_attribute", concept.Event),
    # ("visits", concept.Event),
    ("events", concept.Event),
)

@backcompatapi.route('/v2/sync', methods=['POST'])
@api.route('/sync', methods=['POST'])
def sync_v2_push():
    # _get_authenticated_user_from_request(request)
    last_synced_at = _get_last_pulled_at_from(request)
    schemaVersion = request.args.get("schemaVersion", None)
    migration = request.args.get("migration", None)

    # 2. If the changes object contains a record that has been modified on the server after lastPulledAt, you MUST abort push and return an error code
    
    # expected body structure
    # { [s in 'events' | 'patients' | ....]: { "created": Array<dict[str, any]>, "updated": Array<dict[str, any]>, deleted: []str }}
    body = dict(request.get_json())

    with db.get_connection() as conn:
        try:
            for entitykey, e in _KNOWN_ENTITIES_TO_SYNC_UP:
                if entitykey not in body:
                    continue


                # get the entity delta values
                deltadata = defaultdict(None, body[entitykey])

                # package delta data
                deltadata = sync.DeltaData(
                    created=deltadata.get("created"),
                    updated=deltadata.get("updated"),
                    # deleted=[{"id": id } for id in deltadata.get("deleted")] if deltadata.get("deleted") is not None else None,
                    deleted=deltadata.get("deleted")
                )

                e.apply_delta_changes(deltadata, last_pushed_at=last_synced_at, conn=conn)

            return jsonify({ "ok": True })    
        except Exception as err:
            conn.close()
            print(err)
            print(traceback.format_exc())
            return jsonify({ "ok": False, "message": "failed horribly" })
    

def _get_timestamp_now():
    return time.mktime(datetime.now().timetuple()) * 1000