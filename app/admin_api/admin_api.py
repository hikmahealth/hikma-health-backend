import json
from flask import Blueprint, request, jsonify, send_file
from web_util import assert_data_has_keys, admin_authenticated
from db_util import get_connection
from web_errors import WebError
from users.user import User
from dateutil import parser
from datetime import datetime, timedelta
from patients.patient import Patient
from patients.data_access import all_patient_data, search_patients, patient_additional_attributes
from users.data_access import all_user_data, add_user, delete_user_by_id, user_data_by_email
from language_strings.language_string import LanguageString
from admin_api.patient_data_export import most_recent_export
from admin_api.single_patient_data_export import single_patient_export

import urllib.parse
from urllib.parse import unquote
import uuid
import bcrypt
import psycopg2.errors


admin_api = Blueprint('admin_api', __name__, url_prefix='/admin_api')


@admin_api.route('/login', methods=['POST'])
def login():
    params = assert_data_has_keys(request, {'email', 'password'})
    user = User.authenticate(params['email'], params['password'])
    token = user.create_token()
    return jsonify({'token': token})


@admin_api.route('/logout', methods=['POST'])
@admin_authenticated
def logout(admin_user: User):
    admin_user.logout()
    return jsonify({'message': 'OK'})


@admin_api.route('/is_authenticated', methods=['GET'])
@admin_authenticated
def is_authenticated(_admin_user):
    return jsonify({'message': 'OK'})


@admin_api.route('/all_users', methods=['GET'])
@admin_authenticated
def get_all_users(_admin_user):
    all_users = [User.from_db_row(r).to_dict() for r in all_user_data()]
    return jsonify({'users': all_users})


@admin_api.route('/user', methods=['POST'])
@admin_authenticated
def create_user(_admin_user):
    params = assert_data_has_keys(
        request, {'email', 'password', 'clinic_id', 'name', 'role'})
    if params['role'] not in ['admin', 'provider']:
        raise WebError('Role must be either "admin" or "provider"', 400)

    id = str(uuid.uuid4())
    # language = params.get('language', 'en')
    # name_str = LanguageString(id=str(uuid.uuid4()), content_by_language={language: params['name']})
    hashed_password = bcrypt.hashpw(
        params['password'].encode(), bcrypt.gensalt()).decode()
    user = User(id, params['name'], params['role'],
                params['email'], params["clinic_id"], hashed_password)
    try:
        add_user(user)
    except psycopg2.errors.UniqueViolation:
        raise WebError('User already exists', 409)

    all_users = [User.from_db_row(r).to_dict() for r in all_user_data()]
    return jsonify({'users': all_users})


@admin_api.route('/user', methods=['DELETE'])
@admin_authenticated
def delete_user(_admin_user):
    params = assert_data_has_keys(request, {'email'})
    user = User.from_db_row(user_data_by_email(params['email']))
    delete_user_by_id(user.id)
    all_users = [User.from_db_row(r).to_dict() for r in all_user_data()]
    return jsonify({'users': all_users})


@admin_api.route('/change_password', methods=['POST'])
@admin_authenticated
def change_password(_admin_user):
    params = assert_data_has_keys(request, {'email', 'new_password'})
    user = User.from_db_row(user_data_by_email(params['email']))
    user.reset_password(params['new_password'])
    return jsonify({'message': 'ok'})


# @admin_api.route('/upload', methods=['POST'])
# @admin_authenticated
# def upload_patient_data(_admin_user):
#     if len(request.files) == 0:
#         raise WebError('Files must be present', 400)

#     importer = PatientDataImporter(request.files['file'])
#     importer.run()
#     return jsonify({'message': 'OK'})


@admin_api.route('/export', methods=['POST'])
@admin_authenticated
def export_all_data(_admin_user):
    export_filename = most_recent_export()
    return send_file(export_filename, attachment_filename='hikma_export.xlsx')


@admin_api.route('/all_patients', methods=['GET'])
@admin_authenticated
def get_all_patients(_admin_user):
    # TOMBSTONE: Jun 3 2024
    # all_patients = [Patient.from_db_row(r).to_dict()
    #                 for r in all_patient_data()]
    all_patients = all_patient_data()

    return jsonify({'patients': all_patients})


@admin_api.route('/search_patients', methods=['POST'])
@admin_authenticated
def search(_admin_user):
    params = assert_data_has_keys(
        request, {'given_name', 'surname', 'country', 'hometown'})
    patient = [Patient.from_db_row(r).to_dict() for r in search_patients(
        params['given_name'], params['surname'], params['country'], params['hometown'])]
    return jsonify({'patient': patient})


@admin_api.route('/export_patient', methods=['POST'])
@admin_authenticated
def export_patient_data(_admin_user):
    params = assert_data_has_keys(request, {'patient_id'})
    export_filename = single_patient_export(params['patient_id'])
    return send_file(export_filename, attachment_filename='hikma_patient_export.xlsx')


@admin_api.route('/summary_stats', methods=['GET'])
@admin_authenticated
def get_summary_stats(_admin_user):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # get the total counts for patients, events, visits, users and forms
                cur.execute("SELECT COUNT(*) FROM patients")
                patient_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM events")
                event_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()[0]
                cur.execute(
                    "SELECT COUNT(*) FROM event_forms WHERE is_deleted=FALSE")
                form_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM visits")
                visit_count = cur.fetchone()[0]

            except Exception as e:
                print("Error while getting summary stats: ", e)
                raise e
    return jsonify({'patient_count': patient_count, 'event_count': event_count, 'user_count': user_count, 'form_count': form_count, 'visit_count': visit_count})


@admin_api.route('/save_event_form', methods=['POST'])
@admin_authenticated
def save_event_form(_admin_user):
    params = assert_data_has_keys(request, {'event_form'})
    event_form = params['event_form']
    print("event_form: ", event_form)
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO event_forms (id, name, description, form_fields, metadata, language, is_editable, is_snapshot_form, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        event_form['id'],
                        event_form['name'],
                        event_form['description'],
                        json.dumps(event_form['form_fields']),
                        json.dumps(event_form['metadata']),
                        event_form["language"],
                        event_form["is_editable"],
                        event_form["is_snapshot_form"],
                        event_form['createdAt'],
                        event_form['updatedAt']
                    )
                )
            except Exception as e:
                conn.rollback()
                print("Error while inserting event form: ", e)
                raise e

    return jsonify({'message': 'OK'})


@admin_api.route('/get_event_forms', methods=['GET'])
@admin_authenticated
def get_event_forms(_admin_user):
    event_forms = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT id, name, description, form_fields, metadata, language, is_editable, is_snapshot_form, created_at, updated_at FROM event_forms WHERE is_deleted=FALSE")
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
                print("Error while getting event forms: ", e)
                raise e

    return jsonify({'event_forms': event_forms})


@admin_api.route('/get_event_form', methods=['GET'])
@admin_authenticated
def get_event_form(_admin_user):
    # params = assert_data_has_keys(request, {'id'})
    event_form_id = request.args.get('id')
    event_forms = []
    with get_connection() as conn:
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
                print("Error while getting event form: ", e)
                raise e

    return jsonify({'event_form': event_forms[0]})


@admin_api.route("/update_event_form", methods=["POST"])
@admin_authenticated
def update_event_form(admin_user):
    params = assert_data_has_keys(request, {'id', 'updates'})
    event_form_id = params['id']
    event_form_update = params['updates']
    with get_connection() as conn:
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
                        datetime.now(),
                        datetime.now(),
                        event_form_id
                    )
                )
            except Exception as e:
                conn.rollback()
                print("Error updating event form: ", e)
                raise e
    return jsonify({'message': 'OK'})


# For a given form Id, toggle the is_editable field to either true or false
@admin_api.route("/set_event_form_editable", methods=["POST"])
@admin_authenticated
def set_event_form_editable(admin_user):
    params = assert_data_has_keys(request, {'id', 'is_editable'})
    event_form_id = params['id']
    is_editable = params['is_editable']
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                dt = datetime.now()
                cur.execute(f"""
                    UPDATE event_forms SET is_editable='{is_editable}', last_modified='{dt}' WHERE id='{event_form_id}'
                """)
            except Exception as e:
                conn.rollback()
                print("Error updating event form: ", e)
                raise e
    return jsonify({'message': 'OK'})

# For a given form Id, toggle the is_snapshot_form field to either true or false


@admin_api.route("/toggle_snapshot_form", methods=["POST"])
@admin_authenticated
def toggle_snapshot_form(admin_user):
    params = assert_data_has_keys(request, {'id'})
    event_form_id = params['id']
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                dt = datetime.now()
                cur.execute(f"""
                    UPDATE event_forms SET is_snapshot_form = NOT is_snapshot_form, last_modified='{dt}' WHERE id='{event_form_id}'
                """)
            except Exception as e:
                conn.rollback()
                print("Error updating event form: ", e)
                raise e
    return jsonify({'message': 'OK'})


@admin_api.route('/delete_event_form', methods=['DELETE'])
@admin_authenticated
def delete_event_form(_admin_user):
    params = assert_data_has_keys(request, {'id'})
    event_form_id = params['id']
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                dt = datetime.now()
                # cur.execute("DELETE FROM event_forms WHERE id = %s", (event_form_id,))
                # Flag form as deleted
                cur.execute(f"""
                            UPDATE event_forms SET is_deleted=TRUE, deleted_at='{dt}', last_modified='{dt}' WHERE id='{event_form_id}'
                            """)
            except Exception as e:
                conn.rollback()
                print("Error while deleting event form: ", e)
                raise e

    return jsonify({'message': 'OK'})


@admin_api.route('/update_patient_registration_form', methods=['POST'])
@admin_authenticated
def update_patient_registration_form(_admin_user):
    params = assert_data_has_keys(request, {"form"})
    form = params["form"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                dt = datetime.now()

                # upsert the form using the id field
                # "form" has the the following fields:
                # id: string
                # fields: json
                # metadata: json
                query = f"""
                    INSERT INTO patient_registration_forms(id, name, fields, metadata, is_deleted, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        fields = EXCLUDED.fields,
                        metadata = EXCLUDED.metadata,
                        is_deleted = EXCLUDED.is_deleted,
                        updated_at = EXCLUDED.updated_at,
                        last_modified = NOW();
                """
                cur.execute(query, (
                    form["id"],
                    form["name"],
                    form["fields"],
                    form["metadata"],
                    False,
                    form['createdAt'],
                    form['updatedAt']
                ))
            except Exception as e:
                conn.rollback()
                print("Error while updating the patient registration form: ", e)
                raise e

    return jsonify({'message': 'OK'})


@admin_api.route('/get_patient_registration_forms', methods=['GET'])
@admin_authenticated
def get_patient_registration_forms(_admin_user):
    forms = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                res = cur.execute(
                    "SELECT id, name, fields, metadata, is_deleted, created_at, updated_at FROM patient_registration_forms WHERE is_deleted = false")
                for frm in cur.fetchall():
                    forms.append({
                        "id": frm[0],
                        "name": urllib.parse.unquote(frm[1]),
                        "fields": frm[2],
                        "metadata": frm[3],
                        "isDeleted": frm[4],
                        "createdAt": frm[5],
                        "updatedAt": frm[6]
                    })
            except Exception as e:
                print("Error while updating the patient registration form: ", e)
                raise e

    return jsonify({'forms': forms})


@admin_api.route('/get_clinics', methods=['GET'])
@admin_authenticated
def get_clinics(_admin_user):
    """Returns a list of all clinics in the database"""
    clinics = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                res = cur.execute(
                    "SELECT id, name, is_deleted, created_at, updated_at FROM clinics WHERE is_deleted = false")
                for clinic in cur.fetchall():
                    clinics.append({
                        "id": clinic[0],
                        "name": urllib.parse.unquote(clinic[1]),
                        "isDeleted": clinic[2],
                        "createdAt": clinic[3],
                        "updatedAt": clinic[4]
                    })
            except Exception as e:
                print("Error while updating the patient registration form: ", e)
                raise e

    return jsonify({'clinics': clinics})


@admin_api.route("/get_patients_events", methods=['GET'])
@admin_authenticated
def get_patient_events(_admin_user):
    """Retruns all the formated events as a single table that can be easily rendered"""
    patient_id = request.args.get('id')


@admin_api.route("/get_event_form_data", methods=['GET'])
@admin_authenticated
def get_event_form_data(_admin_user):
    """Retruns all the formated events as a single table that can be easily rendered"""
    form_id = request.args.get('id')
    start_date = request.args.get('start_date')

    try:
        # Convert start_date from string to datetime
        # datetime.datetime.fromisoformat
        start_date = datetime.fromisoformat(unquote(start_date)).replace(hour=0, minute=1, second=1)
    except ValueError:
        start_date = datetime.now() - timedelta(days=14)

    end_date = request.args.get('end_date')
    try:
        end_date = datetime.fromisoformat(unquote(end_date)).replace(hour=23, minute=59, second=59)
    except ValueError:
        end_date = datetime.now().replace(hour=23, minute=59, second=59)

    print(start_date)
    print(end_date)
    events = []

    # CREATE TABLE events (
    #         id uuid PRIMARY KEY,
    #         patient_id uuid REFERENCES patients(id) ON DELETE CASCADE,
    #         visit_id uuid REFERENCES visits(id) ON DELETE CASCADE DEFAULT NULL,
    #         form_id uuid REFERENCES event_forms(id) ON DELETE CASCADE DEFAULT NULL,
    #         event_type TEXT,
    #         form_data JSONB NOT NULL DEFAULT '{}',
    #         metadata JSONB NOT NULL DEFAULT '{}',
    #         is_deleted boolean default false,
    #         created_at timestamp with time zone default now(),
    #         updated_at timestamp with time zone default now(),
    #         last_modified timestamp with time zone default now(),
    #         server_created_at timestamp with time zone default now(),
    #         deleted_at timestamp with time zone default null
    #     )

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""SELECT events.id, events.patient_id, events.visit_id, events.form_id, events.event_type, events.form_data, events.metadata, events.is_deleted, events.created_at, events.updated_at,
                                  patients.*
                                  FROM events
                                  JOIN patients ON events.patient_id = patients.id
                                  WHERE events.form_id = %s AND events.is_deleted = false AND events.created_at >= %s AND events.created_at <= %s
                                  """, (form_id, start_date, end_date))
                
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

    return jsonify({'events': events})
