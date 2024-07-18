
from flask import Blueprint, request, Request, jsonify


from hikmahealth.server.api import middleware, auth
from hikmahealth.server.client import db
from hikmahealth.server.helpers import web as webhelper

from hikmahealth.entity import hh
import hikmahealth.entity.fields as f

from hikmahealth.utils.errors import WebError

from datetime import datetime, date
from dataclasses import dataclass
import dataclasses

from typing import Any
import json

import uuid
import bcrypt

from psycopg.rows import dict_row, class_row
import psycopg.errors

from urllib import parse as urlparse

from hikmahealth.utils.datetime import utc


admin_api = Blueprint('admin_api_backcompat', __name__, url_prefix='/admin_api')
api = Blueprint('api-admin', __name__)


@admin_api.route('/login', methods=['POST'])
@api.route('/auth/login', methods=['POST'])
def login():
    inp = webhelper.assert_data_has_keys(request, { 'email', 'password' })
    u = auth.get_user_from_email(inp['email'], inp['password'])
    token = auth.create_session_token(u)
    return jsonify({ "token": token })


@admin_api.route('/logout', methods=['POST'])
@middleware.authenticated_admin
def logout(u: auth.User):
    auth.invalidate_tokens(u)
    return jsonify({ "ok": True })


@admin_api.route('/is_authenticated', methods=['GET'])
@middleware.authenticated_admin
def is_authenticated(_):
    return jsonify({'message': 'OK'})


@admin_api.route('/all_users', methods=['GET'])
@api.route("/users", methods=['GET'])
@middleware.authenticated_admin
def get_all_users(_):
    with db.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            rows = cur.execute(
                "SELECT * FROM users WHERE is_deleted = FALSE"
            ).fetchall()

            return jsonify({ 'users': rows })


@admin_api.route('/user', methods=['POST'])
@api.route("/users", methods=['POST'])
@middleware.authenticated_admin
def create_user(_):
    params = webhelper.assert_data_has_keys(request,
         {'email', 'password', 'clinic_id', 'name', 'role'})

    if params['role'] not in ['admin', 'provider']:
        raise WebError('Role must be either "admin" or "provider"', 400)

    id = str(uuid.uuid4())

    hashed_password = bcrypt.hashpw(
        params['password'].encode(), bcrypt.gensalt()).decode()

    user: auth.User | None = None

    # movet to auth.create_user(**params)
    try:
        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(
                    """
                    INSERT INTO users
                    (id, name, role, email, clinic_id, hashed_password)
                    VALUES
                    (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (id, params["name"], params['role'], params['email'], params['clinic_id'], hashed_password)
                ).fetchone()

                user = auth.User(**row)
    except psycopg.errors.UniqueViolation:
        raise WebError("user already exists", 409)
    except BaseException:
        raise WebError("failed to create new user. please try again later", 500)

    return jsonify(user.to_dict())


@admin_api.route('/user', methods=['DELETE'])
@middleware.authenticated_admin
def OLD_delete_user(u: auth.User):
    # NOTE:
    # - should there be a rule for who is allowed to delete what?
    #   (the person can technically delete themselves)
    # - why use 'email' instead of user_id ? (this is the same for delete)
    params = webhelper.assert_data_has_keys(request, {'email'})
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM users WHERE email = %s
                """,
                (params['email'], )
            )

        with conn.cursor(row_factory=class_row(auth.User)) as cur:
            all_users = cur.execute(
                """SELECT * FROM users"""
            ).fetchall()


    return jsonify({ "users": all_users })

@api.route("/users/<uid>", methods=["DELETE"])
@middleware.authenticated_admin
def delete_user(_, uid: str):
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM users WHERE id = %s;
                """,
                (uid, )
            )

            if cur.rowcount > 0:
                return jsonify({
                    "ok": True,
                    "message": "user deleted",
                    "details": dict(uid=uid,)
                })

            else:
                return jsonify({
                    "ok": True,
                    "message": "no such user record. might have already been deleted"
                }, 208)

@dataclass
class ReqChangePassword:
    email: str
    new_password: str

@admin_api.route('/change_password', methods=['POST'])
@middleware.authenticated_admin
def OLD_change_user_password(_):
    chg = webhelper.apply_dataclass(request, ReqChangePassword)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            new_password_hashed = bcrypt.hashpw(
                chg.new_password.encode(), bcrypt.gensalt()).decode()

            cur.execute('UPDATE users SET hashed_password = %s WHERE email = %s',
                        [new_password_hashed, chg.email])

    return jsonify({ "ok": True })

@api.route("/users/<uid>/manage/password", methods=['PUT'])
@middleware.authenticated_admin
def change_user_password(_, uid: str):
    b = webhelper.assert_data_has_keys(request, {"new_password"})
    new_password = b["new_password"]

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            new_password_hashed = bcrypt.hashpw(
                new_password.encode(), bcrypt.gensalt()).decode()

            cur.execute('UPDATE users SET hashed_password = %s WHERE id = %s',
                        [new_password_hashed, uid])

    return jsonify({
        "ok": True,
        "message": "updated user password",
    })

@admin_api.route('/all_patients', methods=['GET'])
@api.route("/patients", methods=["GET"])
@middleware.authenticated_admin
def get_patients(_):
    with db.get_connection() as conn:
        with conn.cursor(row_factory=class_row(hh.Patient)) as cur:
            patients = cur.execute(
                """
                SELECT *
                FROM patients
                WHERE is_deleted = false
                """).fetchall()

    return jsonify({ "patients": patients })


@api.route("/patients/<id>", methods=["GET"])
@middleware.authenticated_admin
def get_single_patient(_, id: str):
    with db.get_connection() as conn:
        with conn.cursor(row_factory=class_row(hh.Patient)) as cur:
            patient = cur.execute(
                """
                SELECT * FROM patients
                WHERE is_deleted = false
                AND id = %s
                """,
                [id]).fetchone()

    return jsonify({"patient": patient})

@api.get("/patients/<id>/events")
@middleware.authenticated_admin
def get_patient_events(_, id: str):
    with db.get_connection().cursor(row_factory=class_row(hh.Event)) as cur:
        events = cur.execute(
            """
            SELECT * FROM {}
            WHERE is_deleted = false AND patient_id = %s
            """.format(hh.Event.TABLE_NAME),
            [id]
        ).fetchall()

    return jsonify(events)

@admin_api.route('/search_patients', methods=['POST'])
@api.route("/search/patients", methods=["GET"])
@middleware.authenticated_admin
def search_patients(_):
    searchparams = webhelper.pluck_optional_data_keys(
        request, {'given_name', 'surname', 'hometown'})

    # TODO: aggregate the search params to sql query
    or_clause = []

    for k, v in searchparams.items():
        or_clause.append((f"p.{k} ILIKE %({k})s"))

    # construct the query to search
    complete_query = " AND \n".join(or_clause) if len(or_clause) >= 1 else "1=1"

    with db.get_connection() as conn:
        with conn.cursor(row_factory=class_row(hh.Patient)) as cur:
            patients = cur.execute(
                """
                SELECT *
                FROM patients as p
                WHERE is_deleted = false
                AND {}
                """.format(complete_query),
                { k: v.upper() for k, v in searchparams.items() }
                ).fetchall()

    return jsonify({ "patients": patients })


@admin_api.route('/summary_stats', methods=['GET'])
@api.get("/statistics")
@middleware.authenticated_admin
def get_summary_stats(_):
    with db.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                # get the total counts for patients, events, visits, users and forms
                stats = cur.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM patients) as patient_count,
                        (SELECT count(*) FROM events) as event_count,
                        (SELECT count(*) FROM users) as user_count,
                        (SELECT count(*) FROM event_forms) as form_count,
                        (SELECT count(*) FROM visits) as visit_count
                    """
                ).fetchone()

            except Exception as e:
                print("Error while getting summary stats: ", e)
                raise e

    return jsonify(stats)

@api.post('/event-forms')
@middleware.authenticated_admin
def save_event_form(_):
    # event_form = EventFormData(**request.get_json())
    d = request.get_json()
    _save_event_form(d)
    return jsonify({"ok": True, "message": "event form saved"})

@admin_api.route('/save_event_form', methods=['POST'])
@middleware.authenticated_admin
def OLD_save_event_form(_):
    # event_form = EventFormData(**request.get_json())
    d = webhelper.assert_data_has_keys(request, {'event_form'})
    _save_event_form(d['event_form'])
    return jsonify({"ok": True, "message": "event form saved"})

def _save_event_form(d):
    e = dict(d)
    e.update(
        form_fields=json.dumps(e['form_fields']),
        metadata=json.dumps(e['metadata']),
    )

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_forms
                (id, name, description, form_fields, metadata, language, is_editable, is_snapshot_form, created_at, updated_at)
                VALUES
                (%(id)s, %(name)s, %(description)s, %(form_fields)s::jsonb, %(metadata)s::jsonb, %(language)s, %(is_editable)s, %(is_snapshot_form)s, %(createdAt)s, %(updatedAt)s)
                """,
                e
            )


@admin_api.route('/get_event_forms', methods=['GET'])
@api.get('/event-forms')
@middleware.authenticated_admin
def get_many_event_forms(_):
    event_forms = hh.EventForm.get_all()
    return jsonify({'event_forms': event_forms})


@admin_api.route("/update_event_form", methods=["POST"])
@middleware.authenticated_admin
def OLD_update_event_form(admin_user):
    params = webhelper.assert_data_has_keys(request, {'id', 'updates'})
    event_form_id = params['id']
    event_form_update = params['updates']
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "UPDATE event_forms SET name=%s, description=%s, form_fields=%s, metadata=%s, language=%s, is_editable=%s, is_snapshot_form=%s, updated_at=%s, last_modified=%s WHERE id=%s",
                    (
                        event_form_update['name'],
                        event_form_update['description'],
                        json.dumps(event_form_update['form_fields']),
                        json.dumps(event_form_update['metadata']),
                        event_form_update['language'],
                        event_form_update['is_editable'],
                        event_form_update['is_snapshot_form'],
                        utc.now(),
                        utc.now(),
                        event_form_id
                    )
                )
            except Exception as e:
                conn.rollback()
                print("Error updating event form: ", e)
                raise e
    return jsonify({'message': 'OK'})


@admin_api.route('/get_event_form', methods=['GET'])
@middleware.authenticated_admin
def OLD_get_event_form(_admin_user):
    # params = assert_data_has_keys(request, {'id'})
    event_form_id = request.args.get('id')
    event_forms = []
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(f"""SELECT id, name, description, form_fields, metadata, language, is_editable, is_snapshot_form, created_at, updated_at FROM event_forms WHERE is_deleted=FALSE AND id='{
                            event_form_id}'""")
                for frm in cur.fetchall():
                    event_forms.append({
                        "id": frm[0],
                        "name": frm[1],
                        "description": frm[2],
                        "form_fields": frm[3],
                        "metadata": frm[4],
                        "language": frm[5],
                        "is_editable": frm[6],
                        "is_snapshot_form": frm[7],
                        "createdAt": frm[8],
                        "updatedAt": frm[9]
                    })
            except Exception as e:
                conn.rollback()
                raise e

    return jsonify({'event_form': event_forms[0]})


@api.get('/event-forms/<id>')
@middleware.authenticated_admin
def get_single_event_form(_, id: str):
    event = hh.EventForm.from_id(id)
    return jsonify({ "event": event.to_dict() })


@api.delete('/event-forms/<id>')
@middleware.authenticated_admin
def delete_event_form(_, id: str):
    _perform_event_form_deletion(id)
    return jsonify({ "ok": True })


@admin_api.route('/delete_event_form', methods=['DELETE'])
@middleware.authenticated_admin
def OLD_delete_event_form(_):
    params = webhelper.assert_data_has_keys(request, {'id'})
    _perform_event_form_deletion(params['id'])
    return jsonify({'message': 'OK'})

def _perform_event_form_deletion(id: str):
    """This does the actual event form deletion"""
    with db.get_connection().cursor() as cur:
        cur.execute(
            """UPDATE event_forms
            SET
                is_deleted = TRUE,
                deleted_at = current_timestamp,
                last_modified = current_timestamp
            WHERE
                id = %s AND
                is_deleted = FALSE
            """,
            [id]
        )


@api.patch('/event-forms/<id>')
@middleware.authenticated_admin
def update_event_form(_, id: str):
    updates = webhelper.pluck_optional_data_keys(request, { 'is_editable', 'is_snapshot_form' })

    # this will have the shape
    # name = %s
    fields_to_update = []
    # get the field to update
    for k, v in updates.items():
        # if k in eventform:
        fields_to_update.append((k, v))

    if len(fields_to_update) == 0:
        return jsonify({ "ok": False, "message": "there's nothing to update"}, 208)

    update_string = ",\n".join(list(map(lambda k: f"{k[0]}=%({k[0]})s", fields_to_update)))

    # TODO: move this function to it's own
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE event_forms
                SET
                {},
                last_modified=current_timestamp,
                updated_at=current_timestamp
                WHERE
                    id = %(id)s AND is_deleted = FALSE
                """.format(update_string),
                dict(
                    **updates,
                     id=id)
            )

    return jsonify({ "ok": True })

@api.get("/event-forms/<id>/events")
@middleware.authenticated_admin
def get_event_form_data(_, id: str):
    events_data = _get_event_form_data(id)
    return jsonify(events_data)

@admin_api.route("/get_event_form_data", methods=['GET'])
@middleware.authenticated_admin
def OLD_get_event_form_data(_):
    id = request.args.get('id')
    events_data = _get_event_form_data(id)
    return jsonify({ "events": events_data })


def _get_event_form_data(id: str):
    """Returns all the formated events as a single table that can be easily rendered"""

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where_clause = []
    if start_date is not None:
        start_date = utc.from_datetime(
            datetime.fromisoformat(urlparse.unquote(start_date)))

        where_clause.append(
            "e.created_at >= %(start_date)s"
        )

    if end_date is not None:
        end_date = utc.from_datetime(
            datetime.fromisoformat(urlparse.unquote(end_date)))

        where_clause.append(
            "e.created_at <= %(end_date)s"
        )

    events = []
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""SELECT events.id, events.patient_id, events.visit_id, events.form_id, events.event_type, events.form_data, events.metadata, events.is_deleted, events.created_at, events.updated_at,
                                  patients.*
                                  FROM events
                                  JOIN patients ON events.patient_id = patients.id
                                  WHERE events.form_id = %s AND events.is_deleted = false AND events.created_at >= %s AND events.created_at <= %s
                                  """, (id, start_date, end_date))

                # Get column names from the cursor description
                column_names = [desc[0] for desc in cur.description]

                for entry in cur.fetchall():
                    # Slice the relevant columns for the patient data
                    patient_data = entry[10:]
                    # Create the patient object using 'zip' for pairing
                    patient = dict(zip(column_names[10:], patient_data))

                    events.append({
                        "id": entry[0],
                        "patientId": entry[1],
                        "visitId": entry[2],
                        "formId": entry[3],
                        "eventType": entry[4],
                        "formData": entry[5],
                        "metadata": entry[6],
                        "isDeleted": entry[7],
                        "createdAt": entry[8],
                        "updatedAt": entry[9],
                        "patient": patient
                    })
            except Exception as e:
                print("Error while updating the patient registration form: ", e)
                raise e

        return events

@admin_api.route("/set_event_form_editable", methods=["POST"])
@middleware.authenticated_admin
def OLD_set_event_form_edit_status(_):
    params = webhelper.assert_data_has_keys(request, {'id', 'is_editable'})
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE event_forms
                SET
                    is_editable=%s,
                    last_modified=current_timestamp,
                    updated_at=current_timestamp
                WHERE id = %s AND is_deleted = FALSE
                """,
                (params['is_editable'], params['id'])
            )

    return jsonify({ "ok": True })

@admin_api.route("/toggle_snapshot_form", methods=["POST"])
@middleware.authenticated_admin
def OLD_set_event_form_snapshot_toggle(_):
    params = webhelper.assert_data_has_keys(request, {'id'})
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE event_forms
                SET
                    is_snapshot_form = NOT is_snapshot_form,
                    last_modified = current_timestamp,
                    updated_at = current_timestamp
                WHERE id = %s AND is_deleted = FALSE
                """,
                [params['id']]
            )

    return jsonify({ "ok": True })




@admin_api.route('/get_patient_registration_forms', methods=['GET'])
@api.get("/patient-forms")
@middleware.authenticated_admin
def get_patient_registration_forms(_):
    """Gets the patient registraion forms"""
    forms = hh.PatientRegistrationForm.get_all()
    return jsonify({"forms": forms})

@api.get("/patient-forms/<id>")
@middleware.authenticated_admin
def get_patient_registration_form(_, id: str):
    """Get single patient reistration form"""
    data = hh.PatientRegistrationForm.from_id(id)
    return jsonify(data)


@dataclass
class PatientRegistrationFormData:
    id: str | None
    """None for the situations where `id` is inserted later on"""

    name: str
    metadata: str | None
    fields: str | None
    createdAt: f.UTCDateTime = f.UTCDateTime()
    updatedAt: f.UTCDateTime = f.UTCDateTime()

@admin_api.route('/update_patient_registration_form', methods=['POST'])
@api.post("/patient-form")
@middleware.authenticated_admin
def update_patient_registration_form(_):
    params = webhelper.assert_data_has_keys(request, {"form"})
    form = PatientRegistrationFormData(**params["form"])

    if form.id is None:
        raise WebError("missing id in the patient registration form", 400)

    return jsonify({ "ok": True })

def _patient_registration_form_upsert(data: PatientRegistrationFormData):
    with db.get_connection().cursor() as cur:
        cur.execute(
            """
            INSERT INTO patient_registration_forms(id, name, fields, metadata, is_deleted, created_at, updated_at, last_modified)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, false, %s, %s, current_timestamp)
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    fields = EXCLUDED.fields,
                    metadata = EXCLUDED.metadata,
                    is_deleted = EXCLUDED.is_deleted,
                    updated_at = EXCLUDED.updated_at,
                    last_modified = current_timestamp;
            """.format(hh.PatientRegistrationForm.TABLE_NAME),
            (data.id, data.name, data.fields, data.metadata, data.createdAt, data.updatedAt)
        )

@api.put("/patient-forms/<id>")
@middleware.authenticated_admin
def set_patient_registration_form(_, id:str):
    """This performs an upsert on the patient registration form"""
    form = PatientRegistrationFormData(**request.json())

    # set the ID of the registration form to perform update query for already existing data
    form.id = id

    _patient_registration_form_upsert(form)
    return jsonify({ "ok": True })

@admin_api.route('/get_clinics', methods=['GET'])
@api.get("/clinics")
@middleware.authenticated_admin
def get_all_clinics(_):
    with db.get_connection().cursor(row_factory=dict_row) as cur:
        clinics = cur.execute(
            """
            SELECT
                c.id,
                c.name,
                c.is_deleted as "isDeleted",
                c.created_at as "createdAt",
                c.updated_at as "updatedAt"
            FROM {} as c
            WHERE is_deleted = FALSE
            """.format(hh.Clinic.TABLE_NAME),
        ).fetchall()

    return jsonify({"clinics": clinics})
