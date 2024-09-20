from __future__ import annotations

from hikmahealth.entity import core, sync, fields, helpers

from datetime import datetime
from hikmahealth.utils.datetime import utc

from datetime import date


import itertools

from hikmahealth.server.client import db
from typing import Any

from psycopg.rows import class_row, dict_row
import dataclasses
import json

from hikmahealth.utils.misc import is_valid_uuid

# might want to make it such that the syncing
# 1. fails properly
# 2. not as all or nothing?

# -----
# TO NOTE:
# 1. include docs (with copy-pastable examples) on
# how to create and 'deal' with new concept like the Nurse, when i want to sync up

# When creating an entity, ask youself:
# 1. is the thing syncable (up or down, ... or both)

# TODO: 👇🏽 that one


@core.dataentity
class Patient(sync.SyncableEntity, helpers.SimpleCRUD):
    TABLE_NAME = "patients"

    id: str
    given_name: str | None = None
    surname: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None
    camp: str | None = None
    citizenship: str | None = None
    hometown: str | None = None
    phone: str | None = None
    additional_data: dict | list | None = None

    government_id: str | None = None
    external_patient_id: str | None = None

    created_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        """Applies the delta changes pushed by the client to this server database.

        NOTE: might want to have `DeltaData` as only input and add `last_pushed_at` to deleted"""
        with conn.cursor() as cur:
            # performs upserts (insert + update when existing)
            for row in itertools.chain(deltadata.created, deltadata.updated):
                patient = dict(row)

                # Handle additional_data
                if patient["additional_data"] is None or patient["additional_data"] == '':
                    patient["additional_data"] = '{}'  # Empty JSON object
                elif isinstance(patient["additional_data"], (dict, list)):
                    patient["additional_data"] = json.dumps(
                        patient["additional_data"])
                elif isinstance(patient["additional_data"], str):
                    try:
                        json.loads(patient["additional_data"])
                    except json.JSONDecodeError:
                        # Empty JSON object if invalid
                        patient["additional_data"] = '{}'

                patient.update(
                    created_at=utc.from_unixtimestamp(patient["created_at"]),
                    updated_at=utc.from_unixtimestamp(patient["updated_at"]),
                    image_timestamp=utc.from_unixtimestamp(
                        patient["image_timestamp"]) if "image_timestamp" in patient else None,
                    photo_url="https://cdn.server.fake/image/convincing-id",
                    last_modified=utc.now()
                )

                cur.execute(
                    """INSERT INTO patients
                          (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified)
                        VALUES 
                          (%(id)s, %(given_name)s, %(surname)s, %(date_of_birth)s, %(citizenship)s, %(hometown)s, %(sex)s, %(phone)s, %(camp)s, %(additional_data)s, %(image_timestamp)s, %(photo_url)s, %(government_id)s, %(external_patient_id)s, %(created_at)s, %(updated_at)s, %(last_modified)s)
                        ON CONFLICT (id) DO UPDATE
                        SET given_name = EXCLUDED.given_name,
                            surname = EXCLUDED.surname,
                            date_of_birth = EXCLUDED.date_of_birth,
                            citizenship = EXCLUDED.citizenship,
                            hometown = EXCLUDED.hometown,
                            sex = EXCLUDED.sex,
                            phone = EXCLUDED.phone,
                            camp = EXCLUDED.camp,
                            additional_data = EXCLUDED.additional_data,
                            government_id = EXCLUDED.government_id,
                            external_patient_id = EXCLUDED.external_patient_id,
                            created_at = EXCLUDED.created_at,
                            updated_at = EXCLUDED.updated_at,
                            last_modified = EXCLUDED.last_modified;
                    """,
                    patient
                )

            for id in deltadata.deleted:
                cur.execute(
                    """UPDATE patients SET is_deleted=true, deleted_at=%s WHERE id = %s::uuid;""",
                    (last_pushed_at, id)
                )


@core.dataentity
class PatientAttribute(sync.SyncableEntity):
    TABLE_NAME = "patient_additional_attributes"

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        with conn.cursor() as cur:
            # performs upserts (insert + update when existing)
            for row in itertools.chain(deltadata.created, deltadata.updated):
                pattr = dict(row)
                pattr.update(
                    date_value=utc.from_unixtimestamp(
                        pattr["date_value"]) if pattr.get("date_value", None) else None,
                    created_at=utc.from_unixtimestamp(pattr["created_at"]),
                    updated_at=utc.from_unixtimestamp(pattr["updated_at"]),
                    metadata=pattr["metadata"],
                )

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
                    pattr
                )

            for id in deltadata.deleted:
                cur.execute(
                    """UPDATE patient_additional_attributes SET is_deleted=true, deleted_at=%s WHERE id = %s::uuid;""",
                    (last_pushed_at, id)
                )


@core.dataentity
class Event(sync.SyncableEntity):
    TABLE_NAME = "events"

    patient_id: str
    visit_id: str
    form_id: str
    event_type: str
    form_data: str
    metadata: dict

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        with conn.cursor() as cur:
            # `cur.executemany` can be used instead
            for row in itertools.chain(deltadata.created, deltadata.updated):
                event = dict(row)
                event.update(
                    created_at=utc.from_unixtimestamp(event["created_at"]),
                    updated_at=utc.from_unixtimestamp(event["updated_at"]),
                    metadata=json.dumps(event["metadata"]),
                )

                cur.execute(
                    """
                    INSERT INTO events
                    (id, patient_id, form_id, visit_id, event_type, form_data, metadata, is_deleted, created_at, updated_at, last_modified)   
                    VALUES
                    (%(id)s, %(patient_id)s, %(form_id)s, %(visit_id)s, %(event_type)s, %(form_data)s, %(metadata)s, false, %(created_at)s, %(updated_at)s, current_timestamp)   
                    ON CONFLICT (id) DO UPDATE
                    SET patient_id=EXCLUDED.patient_id,  
                        form_id=EXCLUDED.form_id, 
                        visit_id=EXCLUDED.visit_id, 
                        event_type=EXCLUDED.event_type, 
                        form_data=EXCLUDED.form_data, 
                        metadata=EXCLUDED.metadata, 
                        created_at=EXCLUDED.created_at, 
                        updated_at=EXCLUDED.updated_at, 
                        last_modified=EXCLUDED.last_modified;
                    """,
                    event
                )

            for id in deltadata.deleted:
                cur.execute(
                    """UPDATE events SET is_deleted=true, deleted_at=%s WHERE id = %s;""",
                    (last_pushed_at, id)
                )


@core.dataentity
class Visit(sync.SyncableEntity):
    TABLE_NAME = "visits"

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        with conn.cursor() as cur:
            # `cur.executemany` can be used instead
            for visit in itertools.chain(deltadata.created, deltadata.updated):
                visit = dict(visit)
                visit.update(
                    check_in_timestamp=utc.from_unixtimestamp(
                        visit['check_in_timestamp']),
                    created_at=utc.from_unixtimestamp(visit['created_at']),
                    updated_at=utc.from_unixtimestamp(visit['updated_at']),
                    metadata=json.dumps(visit["metadata"]),
                    last_modified=utc.now()
                )

                cur.execute(
                    """
                    INSERT INTO visits
                        (id, patient_id, clinic_id, provider_id, provider_name, check_in_timestamp, metadata, created_at, updated_at, last_modified)
                    VALUES
                        (%(id)s, %(patient_id)s, %(clinic_id)s, %(provider_id)s, %(provider_name)s, %(check_in_timestamp)s, %(metadata)s, %(created_at)s, %(updated_at)s, %(last_modified)s)   
                    ON CONFLICT (id) DO UPDATE
                    SET
                        patient_id=EXCLUDED.patient_id,  
                        clinic_id=EXCLUDED.clinic_id, 
                        provider_id=EXCLUDED.provider_id, 
                        provider_name=EXCLUDED.provider_name, 
                        check_in_timestamp=EXCLUDED.check_in_timestamp, 
                        metadata=EXCLUDED.metadata, 
                        created_at=EXCLUDED.created_at,
                        updated_at=EXCLUDED.updated_at, 
                        last_modified=EXCLUDED.last_modified
                    """,
                    visit
                )

            for id in deltadata.deleted:
                cur.execute(
                    """UPDATE visits SET is_deleted=true, deleted_at=%s WHERE id=%s;""",
                    (last_pushed_at, id)
                )


@core.dataentity
class Clinic(sync.SyncToClientEntity):
    TABLE_NAME = "clinics"

    id: str
    name: str
    created_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)


@core.dataentity
class PatientRegistrationForm(sync.SyncToClientEntity, helpers.SimpleCRUD):
    TABLE_NAME = "patient_registration_forms"

    id: str
    name: str
    fields: str
    metadata: str
    created_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)


@core.dataentity
class EventForm(sync.SyncToClientEntity, helpers.SimpleCRUD):
    TABLE_NAME = "event_forms"

    id: str
    name: str
    description: str

    metadata: dict
    form_fields: fields.JSON = fields.JSON(default_factory=tuple)
    # metadata: fields.JSON = fields.JSON(default_factory=dict)

    is_editable: bool | None = None
    is_snapshot_form:  bool | None = None
    created_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)

    @classmethod
    def from_id(cls, id: str) -> EventForm:
        with db.get_connection().cursor(row_factory=dict_row) as cur:
            data = cur.execute(
                """
                SELECT * FROM event_forms
                WHERE is_deleted=false AND id = %s
                LIMIT 1
                """,
                (id,)
            ).fetchone()

        return cls(**data)


@core.dataentity
class StringId(sync.SyncToClientEntity):
    TABLE_NAME = "string_ids"


@core.dataentity
class StringContent(sync.SyncToClientEntity):
    TABLE_NAME = "string_content"


@core.dataentity
class Appointment(sync.SyncableEntity):
    TABLE_NAME = "appointments"

    id: str
    timestamp: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    duration: int | None = None  # in minutes
    reason: str | None = None
    notes: str | None = None
    provider_id: str | None = None
    clinic_id: str | None = None
    patient_id: str | None = None
    user_id: str | None = None
    status: str | None = None  # pending, completed, cancelled, confirmed
    current_visit_id: str | None = None
    fulfilled_visit_id: str | None = None
    metadata: dict | None = None
    created_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    is_deleted: bool | None = None
    deleted_at: fields.UTCDateTime | None = None
    last_modified: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)
    server_created_at: fields.UTCDateTime = fields.UTCDateTime(
        default_factory=utc.now)

    # id - uuid
    # timestamp - datetime_tz
    # duration - integer(minutes) - nullable
    # reason - string - nullable but default to empty string
    # notes - string-  - nullable but default to empty string
    # provider_id - uuid {healthcare provider with whome the appointment is with} - nullable
    # clinic_id - uuid(foriegn_id)
    # patient_id - uuid(foriegn_id)
    # user_id - uuid(foriegn_id)
    # status - string - defaults to pending
    # current_visit_id - uuid(foriegn_id)
    # fulfilled_visit_id - uuid(foriegn_id) - nullable
    # metadata - json - defaults to empty json
    # created_at - datetime_tz - defaults to utc now
    # updated_at - datetime_tz - defaults to utc now
    # is_deleted - boolean - defaults to false
    # deleted_at - datetime_tz - defaults to null
    # last_modified - datetime_tz - set in server with utc now
    # server_created_at - datetime_tz - set in server with utc now

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        with conn.cursor() as cur:
            # TODO: `cur.executemany` can be used instead
            for appointment in itertools.chain(deltadata.created, deltadata.updated):
                appointment = dict(appointment)
                appointment.update(
                    timestamp=utc.from_unixtimestamp(
                        appointment['timestamp']),
                    created_at=utc.from_unixtimestamp(
                        appointment['created_at']),
                    updated_at=utc.from_unixtimestamp(
                        appointment['updated_at']),
                    server_created_at=utc.now(),
                    metadata=json.dumps(appointment["metadata"]),
                    last_modified=utc.now()
                )

                # Set provider_id to None if it's not present, empty, or an invalid UUID
                if 'provider_id' not in appointment or not appointment['provider_id'] or not is_valid_uuid(appointment['provider_id']):
                    appointment['provider_id'] = None

                cur.execute(
                    """
                    INSERT INTO appointments
                        (id, timestamp, duration, reason, notes, provider_id, clinic_id, patient_id, user_id, status, current_visit_id, fulfilled_visit_id, metadata, created_at, updated_at, last_modified, is_deleted, server_created_at)
                    VALUES
                        (%(id)s, %(timestamp)s, %(duration)s, %(reason)s, %(notes)s, %(provider_id)s, %(clinic_id)s, %(patient_id)s, %(user_id)s, %(status)s, %(current_visit_id)s, %(fulfilled_visit_id)s, %(metadata)s, %(created_at)s, %(updated_at)s, %(last_modified)s, %(is_deleted)s, %(server_created_at)s)
                    ON CONFLICT (id) DO UPDATE
                    SET
                        timestamp=EXCLUDED.timestamp,
                        duration=EXCLUDED.duration,  
                        reason=EXCLUDED.reason, 
                        notes=EXCLUDED.notes, 
                        provider_id=EXCLUDED.provider_id, 
                        clinic_id=EXCLUDED.clinic_id, 
                        patient_id=EXCLUDED.patient_id, 
                        user_id=EXCLUDED.user_id,
                        status=EXCLUDED.status, 
                        current_visit_id=EXCLUDED.current_visit_id,
                        fulfilled_visit_id=EXCLUDED.fulfilled_visit_id,
                        metadata=EXCLUDED.metadata,
                        created_at=EXCLUDED.created_at,
                        updated_at=EXCLUDED.updated_at,
                        last_modified=EXCLUDED.last_modified,
                        is_deleted=EXCLUDED.is_deleted
                    """,
                    appointment
                )

            for id in deltadata.deleted:
                # Not making 'cancelled' appointments 'deleted' on purpose. we need to sync them
                cur.execute(
                    """UPDATE appointments SET is_deleted=true, deleted_at=%s WHERE id=%s;""",
                    (last_pushed_at, id)
                )

    @classmethod
    def search(cls, filters):
        with db.get_connection().cursor(row_factory=dict_row) as cur:
            query = """
            SELECT 
                a.*,
                json_build_object(
                    'given_name', p.given_name,
                    'surname', p.surname,
                    'date_of_birth', p.date_of_birth,
                    'sex', p.sex,
                    'phone', p.phone
                ) AS patient,
                json_build_object(
                    'name', u.name
                ) AS user,
                json_build_object(
                    'name', c.name
                ) AS clinic
            FROM appointments a
            LEFT JOIN patients p ON a.patient_id = p.id
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN clinics c ON a.clinic_id = c.id
            WHERE a.is_deleted = false
              AND a.timestamp >= %(start_date)s
              AND a.timestamp <= %(end_date)s
            """
            params = {
                'start_date': filters['start_date'],
                'end_date': filters['end_date'],
            }

            # Status could either be pending, fulfilled or cancelled or all or checked_in
            if 'status' in filters and filters['status'] != 'all':
                query += " AND a.status = %(status)s"
                params['status'] = filters['status']

            if 'patient_id' in filters:
                query += " AND a.patient_id = %(patient_id)s"
                params['patient_id'] = filters['patient_id']

            if 'provider_id' in filters:
                query += " AND a.provider_id = %(provider_id)s"
                params['provider_id'] = filters['provider_id']

            if 'clinic_id' in filters:
                query += " AND a.clinic_id = %(clinic_id)s"
                params['clinic_id'] = filters['clinic_id']

            cur.execute(query, params)
            return cur.fetchall()
