from datetime import datetime, timezone
import logging
from flask import Blueprint, request, jsonify


from hikmahealth.server.api import middleware, auth
from hikmahealth.server.client import db
from hikmahealth.server.helpers import web as webhelper

from hikmahealth.entity import hh
import hikmahealth.entity.fields as f

from hikmahealth.utils.misc import convert_dict_keys_to_snake_case, convert_operator
from hikmahealth.utils.errors import WebError
from psycopg import Error as PostgresError

from dataclasses import dataclass, asdict

import json

import uuid
import bcrypt

from psycopg.rows import dict_row, class_row
import psycopg.errors


from hikmahealth.utils.datetime import utc


admin_api = Blueprint('admin_api_backcompat', __name__, url_prefix='/admin_api')
api = Blueprint('api-admin', __name__)


@admin_api.route('/login', methods=['POST'])
@api.route('/auth/login', methods=['POST'])
def login():
    inp = webhelper.assert_data_has_keys(request, {'email', 'password'})
    print(inp)
    u = auth.get_user_from_email(inp['email'], inp['password'])
    token = auth.create_session_token(u)
    return jsonify({'token': token})


@admin_api.route('/logout', methods=['POST'])
@middleware.authenticated_admin
def logout(u: auth.User):
    auth.invalidate_tokens(u)
    return jsonify({'ok': True})


@admin_api.route('/is_authenticated', methods=['GET'])
@middleware.authenticated_admin
def is_authenticated(_):
    return jsonify({'message': 'OK'})


@admin_api.route('/all_users', methods=['GET'])
@api.route('/users', methods=['GET'])
@middleware.authenticated_admin
def get_all_users(_):
    with db.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            rows = cur.execute(
                """
                SELECT clinic_id, email, id, name, role, created_at
                FROM users
                WHERE is_deleted = FALSE
                """
            ).fetchall()

            return jsonify({'users': rows})


@admin_api.route('/user', methods=['POST'])
@api.route('/users', methods=['POST'])
@middleware.authenticated_admin
def create_user(_):
    params = webhelper.assert_data_has_keys(
        request, {'email', 'password', 'clinic_id', 'name', 'role'}
    )

    if params['role'] not in ['admin', 'provider']:
        raise WebError('Role must be either "admin" or "provider"', 400)

    id = str(uuid.uuid4())

    hashed_password = bcrypt.hashpw(
        params['password'].encode(), bcrypt.gensalt()
    ).decode()

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
                    (
                        id,
                        params['name'],
                        params['role'],
                        params['email'],
                        params['clinic_id'],
                        hashed_password,
                    ),
                ).fetchone()

                user = auth.User(**row)
    except psycopg.errors.UniqueViolation:
        raise WebError('user already exists', 409)
    except BaseException:
        raise WebError('failed to create new user. please try again later', 500)

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
                (params['email'],),
            )

        with conn.cursor(row_factory=class_row(auth.User)) as cur:
            all_users = cur.execute("""SELECT * FROM users""").fetchall()

    return jsonify({'users': all_users})


@api.route('/users/<uid>', methods=['DELETE'])
@middleware.authenticated_admin
def delete_user(_, uid: str):
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM users WHERE id = %s;
                """,
                (uid,),
            )

            if cur.rowcount > 0:
                return jsonify({
                    'ok': True,
                    'message': 'user deleted',
                    'details': dict(
                        uid=uid,
                    ),
                })

            else:
                return jsonify(
                    {
                        'ok': True,
                        'message': 'no such user record. might have already been deleted',
                    },
                    208,
                )


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
                chg.new_password.encode(), bcrypt.gensalt()
            ).decode()

            cur.execute(
                'UPDATE users SET hashed_password = %s WHERE email = %s',
                [new_password_hashed, chg.email],
            )

    return jsonify({'ok': True})


@api.route('/users/<uid>/manage/password', methods=['PUT'])
@middleware.authenticated_admin
def change_user_password(_, uid: str):
    b = webhelper.assert_data_has_keys(request, {'new_password'})
    new_password = b['new_password']

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            new_password_hashed = bcrypt.hashpw(
                new_password.encode(), bcrypt.gensalt()
            ).decode()

            cur.execute(
                'UPDATE users SET hashed_password = %s WHERE id = %s',
                [new_password_hashed, uid],
            )

    return jsonify({
        'ok': True,
        'message': 'updated user password',
    })


@api.route('/users/<uid>/manage', methods=['PUT'])
@middleware.authenticated_admin
def update_user_info(_, uid: str):
    try:
        # Get the updated user information from the request
        user_data = webhelper.assert_data_has_keys(
            request, {'name', 'email', 'role', 'clinic_id'}
        )

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Update user information
                cur.execute(
                    """
                    UPDATE users
                    SET name = %s, email = %s, role = %s, clinic_id = %s,
                        updated_at = current_timestamp, last_modified = current_timestamp
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id
                    """,
                    [
                        user_data['name'],
                        user_data['email'],
                        user_data['role'],
                        user_data['clinic_id'],
                        uid,
                    ],
                )
                updated_user = cur.fetchone()

                if not updated_user:
                    return jsonify({'error': 'User not found or already deleted'}), 404

                # Invalidate user tokens
                auth.invalidate_tokens(auth.User(id=uid, **user_data))

            conn.commit()

        return jsonify({
            'ok': True,
            'message': 'User information updated successfully',
            'id': updated_user[0],
        })

    except WebError as we:
        logging.error(f'WebError: {we}')
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@admin_api.route('/all_patients', methods=['GET'])
@api.route('/patients', methods=['GET'])
@middleware.authenticated_with_role(['admin', 'provider', 'super_admin'])
def get_patients(_):
    count = request.args.get('count')
    patients = hh.Patient.get_all_with_attributes(count)
    return jsonify({'patients': patients})
    # with db.get_connection() as conn:
    #     with conn.cursor(row_factory=dict_row) as cur:
    #         patients = cur.execute(patient_with_attrs_query).fetchall()
    # Extract the patient_data from each row since that's where our JSON is
    #         patients = [row['patient_data'] for row in patients]
    #     # with conn.cursor(row_factory=class_row(hh.Patient)) as cur:
    #         # patients = cur.execute(
    #         #     """
    #         #     SELECT *
    #         #     FROM patients
    #         #     WHERE is_deleted = false
    #         #     """
    # ).fetchall()
    # patients = cur.execute(query).fetchall()

    # return jsonify({"patients": patients})


@api.post('/patients')
@middleware.authenticated_admin
def register_patient(_):
    d = webhelper.assert_data_has_keys(request, {'data'})

    # data looks like: { baseFields: {}, attributeFields: [] }
    patient_data = d['data']  # EventFormData(**d["data"])

    patient_id = uuid.uuid1()
    base_fields: dict = patient_data['baseFields']

    base_fields.update(
        id=patient_id,
        created_at=utc.now(),
        updated_at=utc.now(),
        image_timestamp=(
            utc.from_unixtimestamp(base_fields['image_timestamp'])
            if 'image_timestamp' in base_fields
            else None
        ),
        additional_data=base_fields.get('additional_data', '{}'),
        photo_url=base_fields.get('photo_url', ''),
        last_modified=utc.now(),
    )

    attribute_fields = patient_data['attributeFields']

    optional_fields_nullable = ['government_id', 'external_patient_id']
    for field in optional_fields_nullable:
        if field not in base_fields:
            base_fields[field] = None

    optional_fields_empty_string = ['hometown', 'phone', 'camp', 'photo_url']
    for field in optional_fields_empty_string:
        if field not in base_fields:
            base_fields[field] = None

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                        INSERT INTO PATIENTS
                          (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data,
                           image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified)
                        VALUES
                          (%(id)s, %(given_name)s, %(surname)s, %(date_of_birth)s, %(citizenship)s, COALESCE(%(hometown)s, ''), %(sex)s, COALESCE(%(phone)s, ''), COALESCE(%(camp)s, ''), %(additional_data)s, %(image_timestamp)s, COALESCE(%(photo_url)s, ''), COALESCE(%(government_id)s, NULL), COALESCE(%(external_patient_id)s, NULL), %(created_at)s, %(updated_at)s, %(last_modified)s)
                    """,
                    base_fields,
                )

                for pattr in attribute_fields:
                    pattr['patient_id'] = patient_id
                    pattr['created_at'] = utc.now()
                    pattr['updated_at'] = utc.now()
                    pattr['metadata'] = '{}'
                    pattr['last_modified'] = utc.now()
                    cur.execute(
                        """
                        INSERT INTO patient_additional_attributes
                        (id, patient_id, attribute_id, attribute, number_value, string_value, date_value, boolean_value, metadata, is_deleted, created_at, updated_at, last_modified, server_created_at) VALUES
                        (%(id)s, %(patient_id)s, %(attribute_id)s, %(attribute)s, %(number_value)s, %(string_value)s, %(date_value)s, %(boolean_value)s, %(metadata)s, false, %(created_at)s, %(updated_at)s, current_timestamp, current_timestamp)
                        ON CONFLICT (patient_id, attribute_id) DO UPDATE
                        SET
                            patient_id=EXCLUDED.patient_id,
                            attribute_id=EXCLUDED.attribute_id,
                            attribute = EXCLUDED.attribute,
                            number_value = EXCLUDED.number_value,
                            string_value = EXCLUDED.string_value,
                            date_value = EXCLUDED.date_value,
                            boolean_value = EXCLUDED.boolean_value,
                            metadata = EXCLUDED.metadata,
                            updated_at = EXCLUDED.updated_at,
                            last_modified = EXCLUDED.last_modified;""",
                        pattr,
                    )
            except Exception as e:
                conn.rollback()
                print('Error updating event form: ', e)
                raise e

    return jsonify({'ok': True, 'patient_id': str(patient_id)})


@api.route('/patients/<id>', methods=['GET'])
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
                [id],
            ).fetchone()

    return jsonify({'patient': patient})


@api.route('/patients/<id>', methods=['DELETE'])
@middleware.authenticated_admin
def delete_patient(_, id: str):
    with db.get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # Start a transaction
                cur.execute('BEGIN')

                # Check if patient exists
                cur.execute(
                    'SELECT id FROM patients WHERE id = %s AND is_deleted = false', [id]
                )
                if cur.fetchone() is None:
                    return jsonify({'ok': False, 'message': 'Patient not found'}), 404

                # Soft delete the patient and related data
                tables = [
                    'patients',
                    'visits',
                    'events',
                    'appointments',
                    'patient_additional_attributes',
                    'prescriptions',
                ]
                deleted_counts = {}

                for table in tables:
                    cur.execute(
                        f"""
                        UPDATE {table}
                        SET is_deleted = true, deleted_at = current_timestamp
                        WHERE {'id' if table == 'patients' else 'patient_id'} = %s
                        RETURNING id
                        """,
                        [id],
                    )
                    deleted_counts[table] = cur.rowcount

                # Commit the transaction
                cur.execute('COMMIT')

            logging.info(
                f'Patient {id} and related data soft deleted successfully: {deleted_counts}'
            )
            return jsonify({
                'ok': True,
                'message': 'Patient and related data soft deleted successfully',
                'deleted_counts': deleted_counts,
            })

        except psycopg.Error as e:
            conn.rollback()
            logging.error(f'Database error while deleting patient {id}: {str(e)}')
            return (
                jsonify({
                    'ok': False,
                    'message': 'A database error occurred while deleting the patient',
                }),
                500,
            )
        except Exception as e:
            conn.rollback()
            logging.error(f'Unexpected error while deleting patient {id}: {str(e)}')
            return (
                jsonify({
                    'ok': False,
                    'message': 'An unexpected error occurred while deleting the patient',
                }),
                500,
            )


@api.get('/patients/<id>/events')
@middleware.authenticated_admin
def get_patient_events(_, id: str):
    with db.get_connection().cursor(row_factory=class_row(hh.Event)) as cur:
        events = cur.execute(
            """
            SELECT * FROM {}
            WHERE is_deleted = false AND patient_id = %s
            """.format(hh.Event.TABLE_NAME),
            [id],
        ).fetchall()

    return jsonify(events)


@admin_api.route('/search_patients', methods=['POST'])
@api.route('/search/patients', methods=['GET'])
@middleware.authenticated_admin
def search_patients(_):
    query = ''
    if request.method == 'GET':
        query = request.args.get('query')
    else:  # POST
        searchparams = webhelper.pluck_optional_data_keys(request, {'query'})
        query = searchparams.get('query')

    if not query:
        return jsonify({'patients': []})

    # search_query = f"%{query}%"
    patients: list[dict] = list()
    with db.get_connection() as conn:
        patients = hh.Patient.search(query, conn)

    return jsonify({'patients': patients})


@admin_api.route('/summary_stats', methods=['GET'])
@api.get('/statistics')
@middleware.authenticated_admin
def get_summary_stats(_):
    with db.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                # get the total counts for patients, events, visits, users and forms
                stats = cur.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM patients WHERE is_deleted = FALSE) as patient_count,
                        (SELECT count(*) FROM events WHERE is_deleted = FALSE) as event_count,
                        (SELECT count(*) FROM users WHERE is_deleted = FALSE) as user_count,
                        (SELECT count(*) FROM event_forms WHERE is_deleted = FALSE) as form_count,
                        (SELECT count(*) FROM visits WHERE is_deleted = FALSE) as visit_count
                    """
                ).fetchone()

            except Exception as e:
                print('Error while getting summary stats: ', e)
                raise e

    return jsonify(stats)


@api.post('/event-forms')
@middleware.authenticated_admin
def save_event_form(_):
    # event_form = EventFormData(**request.get_json())
    d = EventFormData(**request.get_json())
    _save_event_form(d)
    return jsonify({'ok': True, 'message': 'event form saved'})


@admin_api.route('/save_event_form', methods=['POST'])
@middleware.authenticated_admin
def OLD_save_event_form(_):
    # event_form = EventFormData(**request.get_json())
    d = webhelper.assert_data_has_keys(request, {'event_form'})
    event_form = EventFormData(**d['event_form'])
    _save_event_form(event_form)
    return jsonify({'ok': True, 'message': 'event form saved'})


@dataclass
class EventFormData:
    id: str
    metadata: dict | list | None = None
    name: str | None = None
    description: str | None = None
    form_fields: str | None = None
    """Fields composition that make up the Event Form. Format required as string JSON """
    language: str | None = 'en'
    is_editable: bool | None = True
    is_snapshot_form: bool | None = False
    createdAt: f.UTCDateTime = f.UTCDateTime(default_factory=utc.now)
    updatedAt: f.UTCDateTime = f.UTCDateTime(default_factory=utc.now)

    def to_dict(self):
        return asdict(self)


def _save_event_form(data: EventFormData):
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            data_dict = data.to_dict()

            # remove fields that require database defaults
            data_dict.pop('metadata')
            data_dict.pop('createdAt')
            data_dict.pop('updatedAt')

            # Handle JSON fields
            if data_dict['form_fields']:
                data_dict['form_fields'] = json.dumps(data_dict['form_fields'])

            # Prepare the SQL query
            columns = ', '.join(data_dict.keys())
            placeholders = ', '.join([f'%({k})s' for k in data_dict.keys()])

            query = f"""
                INSERT INTO event_forms
                ({columns})
                VALUES
                ({placeholders})
            """

            # Execute the query
            cur.execute(query, data_dict)
            # cur.execute(
            #     """
            #     INSERT INTO event_forms
            #     (id, name, description, form_fields, metadata, language, is_editable, is_snapshot_form, created_at, updated_at)
            #     VALUES
            #     (%(id)s, %(name)s, %(description)s, %(form_fields)s, %(metadata)s, %(language)s, %(is_editable)s, %(is_snapshot_form)s, %(createdAt)s, %(updatedAt)s)
            #     """,
            #     data
            # )


@admin_api.route('/get_event_forms', methods=['GET'])
@api.get('/event-forms')
@middleware.authenticated_admin
def get_many_event_forms(_):
    event_forms = hh.EventForm.get_all()
    return jsonify({'event_forms': event_forms})


@admin_api.route('/update_event_form', methods=['POST'])
@middleware.authenticated_admin
def OLD_update_event_form(admin_user):
    params = webhelper.assert_data_has_keys(request, {'id', 'updates'})
    event_form_id = params['id']
    event_form_update = params['updates']
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    UPDATE event_forms
                    SET
                        name=%s,
                        description=%s,
                        form_fields=%s,
                        metadata=%s,
                        language=%s,
                        is_editable=%s,
                        is_snapshot_form=%s, updated_at=%s, last_modified=current_timestamp
                    WHERE id=%s
                    """,
                    (
                        event_form_update['name'],
                        event_form_update['description'],
                        json.dumps(event_form_update['form_fields']),
                        json.dumps(event_form_update['metadata']),
                        event_form_update['language'],
                        event_form_update['is_editable'],
                        event_form_update['is_snapshot_form'],
                        utc.now(),
                        event_form_id,
                    ),
                )
            except Exception as e:
                conn.rollback()
                print('Error updating event form: ', e)
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
                cur.execute(
                    f"""SELECT id, name, description, form_fields, metadata, language, is_editable, is_snapshot_form, created_at, updated_at FROM event_forms WHERE is_deleted=FALSE AND id='{
                        event_form_id
                    }'"""
                )
                for frm in cur.fetchall():
                    event_forms.append({
                        'id': frm[0],
                        'name': frm[1],
                        'description': frm[2],
                        'form_fields': frm[3],
                        'metadata': frm[4],
                        'language': frm[5],
                        'is_editable': frm[6],
                        'is_snapshot_form': frm[7],
                        'createdAt': frm[8],
                        'updatedAt': frm[9],
                    })
            except Exception as e:
                conn.rollback()
                raise e

    return jsonify({'event_form': event_forms[0]})


@api.get('/event-forms/<id>')
@middleware.authenticated_admin
def get_single_event_form(_, id: str):
    event = hh.EventForm.from_id(id)
    return jsonify({'event': event.to_dict()})


@api.delete('/event-forms/<id>')
@middleware.authenticated_admin
def delete_event_form(_, id: str):
    _perform_event_form_deletion(id)
    return jsonify({'ok': True})


@admin_api.route('/delete_event_form', methods=['DELETE'])
@middleware.authenticated_admin
def OLD_delete_event_form(_):
    params = webhelper.assert_data_has_keys(request, {'id'})
    _perform_event_form_deletion(params['id'])
    return jsonify({'message': 'OK'})


def _perform_event_form_deletion(id: str):
    """This does the actual event form deletion"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
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
                [id],
            )
        conn.commit()


@api.patch('/event-forms/<id>')
@middleware.authenticated_admin
def update_event_form(_, id: str):
    updates = webhelper.pluck_optional_data_keys(
        request, {'is_editable', 'is_snapshot_form'}
    )

    # this will have the shape
    # name = %s
    fields_to_update = []
    # get the field to update
    for k, v in updates.items():
        # if k in eventform:
        fields_to_update.append((k, v))

    if len(fields_to_update) == 0:
        return jsonify({'ok': False, 'message': "there's nothing to update"}, 208)

    update_string = ',\n'.join(
        list(map(lambda k: f'{k[0]}=%({k[0]})s', fields_to_update))
    )

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
                dict(**updates, id=id),
            )

    return jsonify({'ok': True})


@api.get('/event-forms/<id>/events')
@middleware.authenticated_admin
def get_event_form_data(_, id: str):
    events_data = _get_event_form_data(id)
    return jsonify(events_data)


@admin_api.route('/get_event_form_data', methods=['GET'])
@middleware.authenticated_admin
def OLD_get_event_form_data(_):
    id = request.args.get('id')
    events_data = _get_event_form_data(id)
    return jsonify({'events': events_data})


def _get_event_form_data(id: str):
    """Returns all the formated events as a single table that can be easily rendered"""

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    print('start_date', start_date)
    print('end_date', end_date)
    test_events = hh.Event.get_events_by_form_id(id, start_date, end_date)
    # print(test_events)
    return test_events


@admin_api.route('/set_event_form_editable', methods=['POST'])
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
                (params['is_editable'], params['id']),
            )

    return jsonify({'ok': True})


@admin_api.route('/toggle_snapshot_form', methods=['POST'])
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
                [params['id']],
            )

    return jsonify({'ok': True})


@admin_api.route('/get_patient_registration_forms', methods=['GET'])
@api.get('/patient-forms')
@middleware.authenticated_with_role(['provider', 'admin', 'super_admin'])
def get_patient_registration_forms(_):
    """Gets the patient registraion forms"""
    forms = hh.PatientRegistrationForm.get_all()
    return jsonify({'forms': forms})


@api.get('/patient-forms/<id>')
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


def _patient_registration_form_upsert(data: PatientRegistrationFormData):
    with db.get_connection() as conn:
        with conn.cursor() as cur:
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
                (
                    data.id,
                    data.name,
                    data.fields,
                    data.metadata,
                    data.createdAt,
                    data.updatedAt,
                ),
            )
        conn.commit()


@admin_api.route('/update_patient_registration_form', methods=['POST'])
@api.post('/patient-form')
@middleware.authenticated_admin
def update_patient_registration_form(_):
    try:
        params = webhelper.assert_data_has_keys(request, {'form'})
        form = PatientRegistrationFormData(**params['form'])

        if form.id is None:
            raise WebError('missing id in the patient registration form', 400)

        _patient_registration_form_upsert(form)
        return jsonify({'ok': True})
    except WebError as we:
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        # Log the database error here
        return jsonify({'error': 'Database error occurred', 'details': str(pe)}), 500
    except Exception as e:
        # Log the unexpected error here
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.put('/patient-forms/<id>')
@middleware.authenticated_with_role(['provider', 'admin', 'super_admin'])
def set_patient_registration_form(_, id: str):
    """This performs an upsert on the patient registration form"""
    form = PatientRegistrationFormData(**request.json())

    # set the ID of the registration form to perform update query for already existing data
    form.id = id

    _patient_registration_form_upsert(form)
    return jsonify({'ok': True})


# Clinic Routes


# Api endpoint to create a new clinic given the clinic name
@api.post('/clinics')
@middleware.authenticated_admin
def create_clinic(_):
    try:
        params = webhelper.assert_data_has_keys(request, {'name'})
        id = str(uuid.uuid1())
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                INSERT INTO clinics (id, name, is_deleted, created_at, updated_at, last_modified)
                VALUES (%s, %s, false, current_timestamp, current_timestamp, current_timestamp)
                RETURNING id
                """,
                    [id, params['name']],
                )
                new_clinic_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({
            'ok': True,
            'message': 'Clinic created successfully',
            'id': new_clinic_id,
        })
    except WebError as we:
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.put('/clinics/<id>')
@middleware.authenticated_admin
def update_clinic(_, id: str):
    try:
        params = webhelper.assert_data_has_keys(request, {'name'})
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE clinics
                    SET name = %s, updated_at = current_timestamp, last_modified = current_timestamp
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id
                    """,
                    [params['name'], id],
                )
                updated_clinic = cur.fetchone()

                if not updated_clinic:
                    return (
                        jsonify({'error': 'Clinic not found or already deleted'}),
                        404,
                    )

            conn.commit()
        return jsonify({
            'ok': True,
            'message': 'Clinic updated successfully',
            'id': updated_clinic[0],
        })
    except WebError as we:
        logging.error(f'WebError: {we}')
        return jsonify({'error': 'Clinic not found or already deleted'}), 404
    except PostgresError as pe:
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.get('/clinics/<id>')
@middleware.authenticated_admin
def get_single_clinic(_, id: str):
    try:
        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                clinic = cur.execute(
                    """
                    SELECT
                        id,
                        name,
                        is_deleted as "isDeleted",
                        created_at as "createdAt",
                        updated_at as "updatedAt"
                    FROM clinics
                    WHERE id = %s AND is_deleted = FALSE
                    """,
                    [id],
                ).fetchone()

                if not clinic:
                    return jsonify({'error': 'Clinic not found'}), 404

        return jsonify({'clinic': clinic})
    except PostgresError as pe:
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@admin_api.route('/get_clinics', methods=['GET'])
@api.get('/clinics')
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

    return jsonify({'clinics': clinics})


@api.delete('/clinics/<id>')
@middleware.authenticated_admin
def delete_clinic(_, id: str):
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE clinics
                    SET is_deleted = TRUE, deleted_at = current_timestamp, last_modified = current_timestamp
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id
                    """,
                    [id],
                )
                deleted_clinic = cur.fetchone()

                if not deleted_clinic:
                    return (
                        jsonify({'error': 'Clinic not found or already deleted'}),
                        404,
                    )

        return jsonify({'ok': True, 'message': 'Clinic deleted successfully'})

    except WebError as we:
        logging.error(f'WebError: {we}')
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'Exception: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.get('/appointments/search')
@middleware.authenticated_admin
def get_appointments(_):
    """Get all appointments matching the filters"""
    # filters include start date, end date, patient id, provider id, clinic id
    filters = request.args.to_dict()
    filters = convert_dict_keys_to_snake_case(filters)
    appointments = hh.Appointment.search(filters)

    return jsonify({'appointments': appointments})


@api.put('/appointments/<id>')
@middleware.authenticated_admin
def update_appointment_status(_, id: str):
    try:
        params = webhelper.assert_data_has_keys(request, {'status'})
        new_status = params['status']

        # Validate the status
        valid_statuses = ['pending', 'completed', 'cancelled', 'confirmed']
        if new_status not in valid_statuses:
            return (
                jsonify({
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }),
                400,
            )

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE appointments
                    SET status = %s, updated_at = %s, last_modified = current_timestamp
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id
                    """,
                    (new_status, utc.now(), id),
                )
                updated_appointment = cur.fetchone()

                if not updated_appointment:
                    return (
                        jsonify({'error': 'Appointment not found or already deleted'}),
                        404,
                    )

        return jsonify({
            'ok': True,
            'message': 'Appointment status updated successfully',
        })

    except WebError as we:
        logging.error(f'WebError: {we}')
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        # Log the database error here
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        # Log the unexpected error here
        logging.error(f'Exception: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.post('/appointments')
@middleware.authenticated_with_role(['provider', 'admin', 'super_admin'])
def create_appointment(_):
    try:
        # Convert camelCase keys to snake_case
        snake_case_params = convert_dict_keys_to_snake_case(request.json)

        required_fields = {
            'patient_id',
            'clinic_id',
            'provider_id',
            'user_id',
            'timestamp',
            'duration',
            'reason',
            'notes',
            'status',
        }

        missing_fields = required_fields - set(snake_case_params.keys())
        if missing_fields:
            raise WebError(
                f'Required data not supplied: {", ".join(missing_fields)}',
                400,
            )

        params = snake_case_params

        # Check if patient_id is valid
        patient = hh.Patient.from_id(params['patient_id'])
        if patient is None:
            return jsonify({'error': 'Patient not found'}), 404

        appointment_id = str(uuid.uuid1())
        visit_id = str(uuid.uuid1())

        token = request.headers.get('Authorization', None)

        if token is None:
            logging.error('missing authentication header')
            raise WebError('missing authentication header', 401)

        user = auth.get_user_from_token(token)

        with db.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    # Create visit
                    cur.execute(
                        """
                        INSERT INTO visits (id, patient_id, clinic_id, provider_id, check_in_timestamp, is_deleted, created_at, updated_at, last_modified)
                        VALUES (%s, %s, %s, %s, %s, false, current_timestamp, current_timestamp, current_timestamp)
                        RETURNING id
                        """,
                        [
                            visit_id,
                            params['patient_id'],
                            params['clinic_id'],
                            user.id,
                            params['timestamp'],
                        ],
                    )

                    # Create appointment
                    cur.execute(
                        """
                        INSERT INTO appointments (id, patient_id, clinic_id, provider_id, user_id, current_visit_id, timestamp, duration, reason, notes, status, is_deleted, created_at, updated_at, last_modified, server_created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, 0), COALESCE(%s, 'other'), COALESCE(%s, ''), %s, false, current_timestamp, current_timestamp, current_timestamp, current_timestamp)
                        RETURNING id
                        """,
                        [
                            appointment_id,
                            params['patient_id'],
                            params['clinic_id'],
                            params.get('provider_id') or None,
                            user.id,
                            visit_id,
                            params['timestamp'],
                            params.get('duration'),
                            params.get('reason'),
                            params.get('notes'),
                            params['status'],
                        ],
                    )

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

        return jsonify({
            'ok': True,
            'message': 'Appointment and visit created successfully',
            'appointment_id': appointment_id,
            'visit_id': visit_id,
        })
    except WebError as we:
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        # Log the database error here
        logging.error(f'Database error occurred: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        # Log the unexpected error here
        logging.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.get('/prescriptions/search')
@middleware.authenticated_admin
def get_prescriptions(_):
    """Get all prescriptions matching the filters"""
    # filters include start date, end date, patient id, provider id, clinic id
    filters = request.args.to_dict()
    filters = convert_dict_keys_to_snake_case(filters)
    prescriptions = hh.Prescription.search(filters)

    return jsonify({'prescriptions': prescriptions})


@api.put('/prescriptions/<id>')
@middleware.authenticated_admin
def update_prescription_status(_, id: str):
    try:
        params = webhelper.assert_data_has_keys(request, {'status'})
        new_status = params['status']

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE prescriptions
                    SET status = %s, updated_at = %s, last_modified = current_timestamp
                    WHERE id = %s AND is_deleted = FALSE
                    RETURNING id
                    """,
                    (new_status, utc.now(), id),
                )
                updated_prescription = cur.fetchone()

                if not updated_prescription:
                    return (
                        jsonify({'error': 'Prescription not found or already deleted'}),
                        404,
                    )

        return jsonify({
            'ok': True,
            'message': 'Prescription status updated successfully',
        })

    except WebError as we:
        logging.error(f'WebError: {we}')
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        # Log the database error here
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        # Log the unexpected error here
        logging.error(f'Exception: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


# =============================================================================
# START OF DATA EXPLORER ENDPOINTS
# =============================================================================


@api.post('/data-explorer')
@middleware.authenticated_with_role(['admin', 'super_admin', 'provider', 'researcher'])
def explore_data(_):
    try:
        filters = request.get_json()

        # Validate the input structure
        if not isinstance(filters, dict):
            return jsonify({'error': 'Invalid filter format'}), 400

        required_keys = ['patient', 'appointment', 'event', 'prescription']
        if not all(key in filters for key in required_keys):
            return jsonify({'error': 'Missing required fields'}), 400

        results = {}

        patient_ids = set()

        # Process the filters
        if filters['event'] and isinstance(filters['event'], list):
            # Event filters' fieldId is ';' separated like: 'formId;fieldId'
            # The operators and values are as they are expressed in the patients filter
            events_results = []  # Store results outside the connection block
            with db.get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    for event_filter in filters['event']:
                        operator = convert_operator(event_filter['operator'])
                        form_id, field_id = event_filter['fieldId'].split(';')
                        query = """
                            SELECT e.*
                            FROM events e
                            WHERE e.form_id = %s AND e.is_deleted = FALSE
                        """
                        params = [form_id]

                        print('OPERATOR: ', operator)
                        print('FIELD ID: ', field_id)

                        if operator == '=':
                            query += """
                                AND EXISTS (
                                    SELECT 1 FROM jsonb_array_elements(e.form_data::jsonb) AS field
                                    WHERE field->>'fieldId' = %s AND field->>'value' = %s
                                )
                            """
                            params.extend([field_id, str(event_filter['value'])])
                        elif operator in ['ILIKE', 'LIKE']:
                            query += """
                                AND EXISTS (
                                    SELECT 1 FROM jsonb_array_elements(e.form_data::jsonb) AS field
                                    WHERE field->>'fieldId' = %s AND field->>'value' ILIKE %s
                                )
                            """
                            params.extend([field_id, f'%{event_filter["value"]}%'])
                        elif operator in ['<', '>', '<=', '>=', '!=']:
                            input_type_query = "field->>'value' {0} %s".format(operator)
                            value = str(event_filter['value'])

                            print('VALUE: ', value)

                            # dataType is one of: number, text, date or boolean
                            if event_filter['dataType'] == 'date':
                                # Handle ISO format date strings by casting through timestamp
                                input_type_query = """
                                    field->>'value' IS NOT NULL
                                    AND field->>'value' != ''
                                    AND (field->>'value')::timestamp {0} %s::timestamp
                                """.format(operator)
                            elif event_filter['dataType'] == 'number':
                                input_type_query = """
                                    field->>'value' IS NOT NULL
                                    AND field->>'value' != ''
                                    AND field->>'value'::numeric {0} %s::numeric
                                """.format(operator)
                            elif event_filter['dataType'] == 'boolean':
                                input_type_query = (
                                    "field->>'value'::boolean {0} %s::boolean".format(
                                        operator
                                    )
                                )

                            query += """
                                AND EXISTS (
                                    SELECT 1 FROM jsonb_array_elements(e.form_data::jsonb) AS field
                                    WHERE field->>'fieldId' = %s
                                    AND {1}
                                )
                            """.format(operator, input_type_query)
                            params.extend([field_id, value])
                        else:
                            query += """
                                AND EXISTS (
                                    SELECT 1 FROM jsonb_array_elements(e.form_data::jsonb) AS field
                                 WHERE field->>'fieldId' = %s AND field->>'value' {} %s
                                )
                            """.format(operator)
                            params.extend([field_id, str(event_filter['value'])])

                        cur.execute(query, params)
                        events_results.extend(cur.fetchall())

            # Process results after connection is closed
            results['events'] = events_results
            for event in events_results:
                patient_ids.add(event['patient_id'])

        if filters['appointment']:
            pass

        if filters['prescription']:
            pass

        print('patient_ids', patient_ids)

        # Process the patient filter last, to take into account any of the other filters
        # including any patient ids that are explicitly set to be limited to
        # TODO: If the patient ids is not empty, only return patients that are in that set
        if filters['patient']:
            patient_filter = filters['patient']
            with db.get_connection() as conn:
                # base_query = """
                #     SELECT DISTINCT p.*
                #     FROM patients p
                # """
                base_query = """
                    WITH distinct_patients AS (
                        SELECT DISTINCT p.*
                        FROM patients p
                    )
                    SELECT dp.id,
                           dp.given_name,
                           dp.surname,
                           dp.date_of_birth,
                           dp.sex,
                           dp.camp,
                           dp.citizenship,
                           dp.hometown,
                           dp.phone,
                           dp.government_id,
                           dp.external_patient_id,
                           dp.created_at,
                           dp.updated_at,
                           dp.last_modified,
                           dp.server_created_at,
                           dp.deleted_at,
                    COALESCE(json_object_agg(
                        pa.attribute_id,
                        json_build_object(
                            'attribute', pa.attribute,
                            'number_value', pa.number_value,
                            'string_value', pa.string_value,
                            'date_value', pa.date_value,
                            'boolean_value', pa.boolean_value
                        )
                    ) FILTER (WHERE pa.attribute_id IS NOT NULL), '{}') AS additional_attributes
                    FROM distinct_patients dp
                    LEFT JOIN patient_additional_attributes pa ON dp.id = pa.patient_id AND pa.is_deleted = false
                """

                where_clauses = []
                params = {}

                # Process base fields
                if patient_filter.get('baseFields'):
                    for rule in patient_filter['baseFields']:
                        operator = convert_operator(rule['operator'])
                        param_name = f'p_{rule["id"]}'
                        where_clauses.append(
                            f'dp.{rule["field"]} {operator} %({param_name})s'
                        )
                        # Add wildcards for contains/does not contain operators
                        if operator in ('ILIKE', 'NOT ILIKE'):
                            params[param_name] = f'%{rule["value"]}%'
                        else:
                            params[param_name] = rule['value']

                # Process attribute fields
                if patient_filter.get('attributeFields'):
                    for rule in patient_filter['attributeFields']:
                        join_alias = f'paa_{rule["id"].replace("-", "_")}'
                        base_query += f"""
                            LEFT JOIN patient_additional_attributes {join_alias}
                            ON dp.id = {join_alias}.patient_id
                            AND {join_alias}.attribute_id = %(attr_id_{join_alias})s
                            AND {join_alias}.is_deleted = false
                        """
                        params[f'attr_id_{join_alias}'] = rule['fieldId']

                        operator = convert_operator(rule['operator'])
                        param_name = f'a_{rule["id"]}'

                        # Build the COALESCE expression to check all possible value types
                        value_expr = f'COALESCE({join_alias}.string_value, CAST({join_alias}.number_value AS TEXT), CAST({join_alias}.boolean_value AS TEXT), CAST({join_alias}.date_value AS TEXT))'

                        where_clauses.append(
                            f'{value_expr} {operator} %({param_name})s'
                        )

                        # Add wildcards for contains/does not contain operators
                        if operator in ('ILIKE', 'NOT ILIKE'):
                            params[param_name] = f'%{rule["value"]}%'
                        else:
                            params[param_name] = rule['value']

                # Add patient_ids filter if other filters exist
                other_filters_exist = (
                    isinstance(filters['event'], list)
                    and len(filters['event']) > 0
                    or filters['appointment']
                    or filters['prescription']
                )
                if other_filters_exist:
                    where_clauses.append('dp.id = ANY(%(patient_ids)s)')
                    params['patient_ids'] = list(patient_ids)

                # Add all WHERE conditions at once if any exist
                if where_clauses:
                    base_query += ' WHERE ' + ' AND '.join(where_clauses)

                # Add GROUP BY since we're using aggregation
                base_query += """
                    GROUP BY dp.id,
                           dp.given_name,
                           dp.surname,
                           dp.date_of_birth,
                           dp.sex,
                           dp.camp,
                           dp.citizenship,
                           dp.hometown,
                           dp.phone,
                           dp.government_id,
                           dp.external_patient_id,
                           dp.created_at,
                           dp.updated_at,
                           dp.last_modified,
                           dp.server_created_at,
                           dp.deleted_at
                """

                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(base_query, params)
                    patients = cur.fetchall()

                    # Process the results
                    for patient in patients:
                        # Convert datetime objects to ISO format strings
                        for key in [
                            'created_at',
                            'updated_at',
                            'last_modified',
                            'deleted_at',
                        ]:
                            if patient[key]:
                                patient[key] = patient[key].isoformat()

                        # Convert date objects to ISO format strings
                        if patient['date_of_birth']:
                            patient['date_of_birth'] = patient[
                                'date_of_birth'
                            ].isoformat()

                    results['patients'] = patients

        return jsonify({
            'ok': True,
            'message': 'Data exploration successful',
            'data': results,
        })

    except WebError as we:
        logging.error(f'WebError: {we}')
        return jsonify({'error': str(we)}), we.status_code
    except PostgresError as pe:
        # Log the database error here
        logging.error(f'PostgresError: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        # Log the unexpected error here
        logging.error(f'Exception: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


# =============================================================================
# END OF DATA EXPLORER ENDPOINTS
# =============================================================================


# =============================================================================
# START OF DATABASE IMPORT & EXPORT ENDPOINTS
# =============================================================================


@api.get('/database/export')
@middleware.authenticated_admin
def export_full_database(_):
    """Downloads all data from the database in JSON format"""
    try:
        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Define tables to export in order of dependencies
                tables = [
                    'clinics',
                    'users',
                    'patients',
                    'patient_additional_attributes',
                    'visits',
                    'events',
                    'event_forms',
                    'patient_registration_forms',
                    'appointments',
                    'string_ids',
                    'string_content',
                    'prescriptions',
                ]

                data = {}

                for table in tables:
                    cur.execute(
                        f"""
                        SELECT *
                        FROM {table}
                        """
                    )
                    results = cur.fetchall()
                    data[table] = results

                return jsonify({
                    'exported_at': datetime.now(timezone.utc).isoformat(),
                    'schema_version': '1.0',
                    'data': data,
                })

    except Exception as e:
        logging.error(f'Error during database export: {str(e)}')
        return jsonify({'error': 'An error occurred during export'}), 500


@api.post('/database/import')
@middleware.authenticated_admin
def import_full_database(_):
    """Imports a full database dump, with transaction rollback on failure"""

    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()

    if 'data' not in data:
        return jsonify({'error': 'Missing data field'}), 400

    tables = data['data']

    # Define columns that should be treated as JSON
    json_columns = {
        'events': ['form_data', 'metadata'],
        'prescriptions': ['items', 'metadata'],
        # "prescriptions": ["metadata"],
        'event_forms': ['metadata'],
        'patient_registration_forms': ['fields', 'metadata'],
        'patients': ['additional_data', 'metadata'],
        'patient_additional_attributes': ['metadata'],
        'visits': ['metadata'],
        'appointments': ['metadata'],
    }

    # Define primary key constraints for each table
    table_primary_keys = {
        'clinics': ['id'],
        'users': ['id'],
        'patients': ['id'],
        # composite key
        'prescriptions': ['id'],
        'patient_additional_attributes': ['patient_id', 'attribute_id'],
        'event_forms': ['id'],
        'visits': ['id'],
        'events': ['id'],
        'patient_registration_forms': ['id'],
        'appointments': ['id'],
        'string_ids': ['id'],
        'string_content': None,  # No UPSERT for this table
    }

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('BEGIN')

                for table_name in [
                    'clinics',
                    'users',
                    'patients',
                    'patient_additional_attributes',
                    'event_forms',
                    'visits',
                    'events',
                    'patient_registration_forms',
                    'appointments',
                    'string_ids',
                    'string_content',
                    'prescriptions',
                ]:
                    if table_name not in tables:
                        raise Exception(f'Table {table_name} not found in data')

                    records = tables[table_name]
                    if not records:
                        continue

                    columns = records[0].keys()
                    column_str = ', '.join(f'"{col}"' for col in columns)
                    value_str = ', '.join(f'%({col})s' for col in columns)

                    # Generate appropriate query based on primary keys
                    primary_keys = table_primary_keys.get(table_name)
                    if primary_keys is None:
                        # Simple INSERT for tables without UPSERT
                        query = f"""
                            INSERT INTO {table_name} ({column_str})
                            VALUES ({value_str})
                        """
                    else:
                        # UPSERT with specified primary keys
                        primary_key_str = ', '.join(primary_keys)
                        update_str = ', '.join([
                            f'"{col}" = EXCLUDED."{col}"'
                            for col in columns
                            if col not in primary_keys
                        ])

                        query = f"""
                            INSERT INTO {table_name} ({column_str})
                            VALUES ({value_str})
                            ON CONFLICT ({primary_key_str}) DO UPDATE SET
                            {update_str}
                        """

                    # Execute each record individually to better handle errors
                    for record in records:
                        try:
                            processed_record = {}
                            for key, value in record.items():
                                if isinstance(value, datetime):
                                    processed_record[key] = value.isoformat()
                                # Handle JSON columns
                                elif (
                                    table_name in json_columns
                                    and key in json_columns[table_name]
                                ):
                                    if isinstance(value, (dict, list)):
                                        processed_record[key] = json.dumps(value)
                                    else:
                                        processed_record[key] = value
                                else:
                                    processed_record[key] = value

                            cur.execute(query, processed_record)
                        except Exception as e:
                            logging.error(
                                f"""Error importing record in {table_name}: {str(e)}"""
                            )
                            logging.error(f'Record: {record}')
                            raise

                # Commit transaction
                cur.execute('COMMIT')

                return jsonify({
                    'ok': True,
                    'message': 'Database import completed successfully',
                    'records_imported': {
                        table: len(records) for table, records in tables.items()
                    },
                })

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logging.error(f'Error during database import: {str(e)}')
        return jsonify({
            'error': 'An error occurred during import',
            'details': str(e),
        }), 500


# =============================================================================
# END OF DATABASE IMPORT & EXPORT ENDPOINTS
# =============================================================================


# AHR Specific Analysis Routes - used for experimenting with analysis endpoints
# Required outputs:
# 1. Patients breakdown by sex and age (age uses the date_of_birth field combined with the "age" dynamic field in patient_additional_attributes table)
# 2. Appointments breakdown by clinic
# 3. Events breakdown by event form
# 4. Event breakdown by clinic - Show the number of events for each clinic
# 5. Breakdown by the number of assigned diagnoses by each provider. This data can be present in any created form / event, it could either be a field called "diagnosis" or "patient diagnosis", etc. a list will be provided.
# 6. Breakdown prescriptions by the medication name.


@api.get('/ahr/patients_breakdown')
@middleware.authenticated_admin
def get_ahrs_patients_breakdown(_):
    """Get the patients breakdown by sex and age"""
    count = request.args.get('count')
    patients = hh.Patient.get_all_with_attributes(count)
    return jsonify({'patients': patients})


@api.get('/ahr/events_by_clinic')
@middleware.authenticated_admin
def get_events_by_clinic(_):
    """Get the breakdown of events by clinic with optional date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        count = request.args.get('count')

        query = """
            SELECT c.name AS clinic_name, COUNT(e.id) AS event_count
            FROM clinics c
            LEFT JOIN visits v ON c.id = v.clinic_id
            LEFT JOIN events e ON v.id = e.visit_id
            WHERE c.is_deleted = FALSE
              AND (v.is_deleted = FALSE OR v.is_deleted IS NULL)
              AND (e.is_deleted = FALSE OR e.is_deleted IS NULL)
        """
        params = []

        if start_date:
            query += ' AND e.created_at >= %s'
            params.append(datetime.fromisoformat(start_date))
        if end_date:
            query += ' AND e.created_at <= %s'
            params.append(datetime.fromisoformat(end_date))

        query += """
            GROUP BY c.id, c.name
            ORDER BY event_count DESC
        """

        if count:
            query += ' LIMIT %s'
            params.append(int(count))

        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                results = cur.fetchall()

        events_by_clinic = {row['clinic_name']: row['event_count'] for row in results}
        return jsonify({
            'events_by_clinic': events_by_clinic,
            'start_date': start_date,
            'end_date': end_date,
        })
    except ValueError as ve:
        logging.error(f'Invalid date format: {ve}')
        return (
            jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}),
            400,
        )
    except PostgresError as pe:
        logging.error(f'Database error occurred: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.get('/ahr/events_by_clinic_through_appointments')
@middleware.authenticated_admin
def get_events_by_clinic_through_appointments(_):
    """
    Get the breakdown of events by clinic through the appointments table.

    Appointments table has a field called "clinic_id" which is the clinic the appointment is for.
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        count = request.args.get('count')

        query = """
            SELECT c.name AS clinic_name, COUNT(a.id) AS appointment_count
            FROM clinics c
            LEFT JOIN appointments a ON c.id = a.clinic_id
            WHERE c.is_deleted = FALSE
              AND (a.is_deleted = FALSE OR a.is_deleted IS NULL)
              AND a.status NOT IN ('pending', 'cancelled')
        """
        params = []

        if start_date:
            query += ' AND a.timestamp >= %s'
            params.append(datetime.fromisoformat(start_date))
        if end_date:
            query += ' AND a.timestamp <= %s'
            params.append(datetime.fromisoformat(end_date))

        query += """
            GROUP BY c.id, c.name
            ORDER BY appointment_count DESC
        """

        if count:
            query += ' LIMIT %s'
            params.append(int(count))

        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                results = cur.fetchall()

        events_by_clinic = {
            row['clinic_name']: row['appointment_count'] for row in results
        }
        return jsonify({
            'events_by_clinic': events_by_clinic,
            'start_date': start_date,
            'end_date': end_date,
        })
    except ValueError as ve:
        logging.error(f'Invalid date format: {ve}')
        return (
            jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}),
            400,
        )
    except PostgresError as pe:
        logging.error(f'Database error occurred: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.get('/ahr/diagnoses_counts')
@middleware.authenticated_admin
def get_diagnoses_counts(_):
    """Get the breakdown of diagnoses"""
    event_form_diagnosis_columns = [
        'diagnosis',
        'Diagnosis',
        'Diagnosis ',
        'patient_diagnosis',
        'Patient Diagnosis',
        'diagnoses',
    ]
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        count = request.args.get('count')

        diagnoses_tally = {}

        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Get all event forms
                cur.execute('SELECT id FROM event_forms WHERE is_deleted = FALSE')
                event_forms = cur.fetchall()

                for form in event_forms:
                    # Get events for this form
                    query = """
                    SELECT form_data
                    FROM events
                    WHERE form_id = %s AND is_deleted = FALSE
                    """
                    params = [form['id']]

                    if start_date:
                        query += ' AND created_at >= %s'
                        params.append(datetime.fromisoformat(start_date))
                    if end_date:
                        query += ' AND created_at <= %s'
                        params.append(datetime.fromisoformat(end_date))

                    cur.execute(query, params)
                    events = cur.fetchall()

                    for event in events:
                        # print(event)
                        # form_data = json.loads(event['form_data'])
                        form_data = event['form_data']
                        # form_data_fields = form_data.get("fields", [])
                        for field in form_data:
                            if (
                                field['name'] in event_form_diagnosis_columns
                                and field['value']
                            ):
                                if isinstance(field['value'], str):
                                    diagnoses = [
                                        d.strip()
                                        for d in field['value'].split(';')
                                        if d.strip()
                                    ]
                                    for diagnosis in diagnoses:
                                        diagnoses_tally[diagnosis] = (
                                            diagnoses_tally.get(diagnosis, 0) + 1
                                        )

                                elif isinstance(field['value'], list):
                                    for item in field['value']:
                                        if (
                                            isinstance(item, dict)
                                            and 'value' in item
                                            and isinstance(item['value'], list)
                                        ):
                                            for diagnosis in item['value']:
                                                if (
                                                    isinstance(diagnosis, dict)
                                                    and 'desc' in diagnosis
                                                ):
                                                    diagnosis_name = diagnosis[
                                                        'desc'
                                                    ].strip()
                                                    if diagnosis_name:
                                                        diagnoses_tally[
                                                            diagnosis_name
                                                        ] = (
                                                            diagnoses_tally.get(
                                                                diagnosis_name, 0
                                                            )
                                                            + 1
                                                        )
                                else:
                                    continue
                                diagnoses_tally[diagnosis] = (
                                    diagnoses_tally.get(diagnosis, 0) + 1
                                )

        # Sort the tally by count in descending order
        sorted_tally = sorted(diagnoses_tally.items(), key=lambda x: x[1], reverse=True)

        # Limit the results if count is specified
        if count:
            sorted_tally = sorted_tally[: int(count)]

        return jsonify({
            'diagnoses_counts': dict(sorted_tally),
            'start_date': start_date,
            'end_date': end_date,
        })

    except ValueError as ve:
        logging.error(f'Invalid date format: {ve}')
        return (
            jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}),
            400,
        )
    except PostgresError as pe:
        logging.error(f'Database error occurred: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api.get('/ahr/prescriptions_counts')
@middleware.authenticated_admin
def get_prescriptions_counts(_):
    """Get the breakdown of prescriptions"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        count = request.args.get('count')

        query = """
            SELECT items from prescriptions
            WHERE is_deleted = FALSE
        """
        params = []

        if start_date:
            query += ' AND created_at >= %s'
            params.append(datetime.fromisoformat(start_date))
        if end_date:
            query += ' AND created_at <= %s'
            params.append(datetime.fromisoformat(end_date))

        if count:
            query += ' LIMIT %s'
            params.append(int(count))

        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                prescriptions = cur.fetchall()

        prescriptions_tally = {}
        for prescription in prescriptions:
            # eg: # "[{\"id\":\"0.13445959591591128\",\"name\":\"Betaval Cream\",\"route\":\"topical\",\"form\":\"cream\",\"frequency\":\"\",\"intervals\":\"\",\"dose\":0,\"doseUnits\":\"mg\",\"duration\":0,\"durationUnits\":\"\",\"medicationId\":\"\",\"quantity\":0,\"status\":\"pending\",\"priority\":\"normal\",\"filledAt\":null,\"filledByUserId\":null}]"
            items = prescription['items']
            items_json = json.loads(items)
            for item in items_json:
                # Convert to lowercase for case-insensitive comparison
                medication_name = item['name'].strip().lower()
                if medication_name:
                    prescriptions_tally[medication_name] = (
                        prescriptions_tally.get(medication_name, 0) + 1
                    )

        # Sort the tally by count in descending order
        sorted_tally = sorted(
            prescriptions_tally.items(), key=lambda x: x[1], reverse=True
        )

        return jsonify({
            'prescriptions_counts': dict(sorted_tally),
            'start_date': start_date,
            'end_date': end_date,
        })
    except ValueError as ve:
        logging.error(f'Invalid date format: {ve}')
        return (
            jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}),
            400,
        )
    except PostgresError as pe:
        logging.error(f'Database error occurred: {pe}')
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500
