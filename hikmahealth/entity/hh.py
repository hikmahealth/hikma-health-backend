from __future__ import annotations

from hikmahealth.entity import core, sync, fields, helpers

from datetime import datetime
from hikmahealth.utils.datetime import utc

from datetime import  date


import itertools

from hikmahealth.server.client import db
from typing import Any

from psycopg.rows import class_row, dict_row
import dataclasses
import json

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
    sex: str | None = None 
    surname: str | None = None 
    date_of_birth: date | None = None
    sex: str | None = None 
    hometown: str | None = None 
    phone: str | None = None 
    additional_data: dict | list | None = None
    
    government_id: str | None = None 
    external_patient_id: str | None = None 

    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        """Applies the delta changes pushed by the client to this server database.
        
        NOTE: might want to have `DeltaData` as only input and add `last_pushed_at` to deleted"""
        with conn.cursor() as cur:
            # performs upserts (insert + update when existing)
            for row in itertools.chain(deltadata.created, deltadata.updated):
                patient = dict(row)
                # print(patient)

                patient.update(
                    created_at=utc.from_unixtimestamp(patient["created_at"]),
                    updated_at=utc.from_unixtimestamp(patient["updated_at"]),
                    image_timestamp=utc.from_unixtimestamp(patient["image_timestamp"]) if "image_timestamp" in patient else None,
                    additional_data=patient["additional_data"],
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
                    date_value=utc.from_unixtimestamp(pattr["date_value"]) if pattr.get("date_value", None) else None,
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
                    SET patient_id=EXCLUDED.patient_id',  
                        form_id=EXCLUDED.form_id', 
                        visit_id=EXCLUDED.visit_id', 
                        event_type=EXCLUDED.event_type', 
                        form_data=EXCLUDED.form_data', 
                        metadata=EXCLUDED.metadata', 
                        created_at=EXCLUDED.created_at', 
                        updated_at=EXCLUDED.updated_at', 
                        last_modified=EXCLUDED.last_modified';
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
                    check_in_timestamp=utc.from_unixtimestamp(visit['check_in_timestamp']),
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
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

@core.dataentity
class PatientRegistrationForm(sync.SyncToClientEntity, helpers.SimpleCRUD):
    TABLE_NAME = "patient_registration_forms"

    id: str
    name: str
    fields: str
    metadata: str
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

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
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

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
            # `cur.executemany` can be used instead
            for appointment in itertools.chain(deltadata.created, deltadata.updated):
                appointment = dict(appointment)
                appointment.update(
                    created_at=utc.from_unixtimestamp(appointment['created_at']),
                    updated_at=utc.from_unixtimestamp(appointment['updated_at']),
                    metadata=json.dumps(appointment["metadata"]),
                    last_modified=utc.now()
                )

                cur.execute(
                    """
                    INSERT INTO appointments
                        (id, timestamp, duration, reason, notes, provider_id, clinic_id, patient_id, user_id, status, current_visit_id, fufilled_visit_id, metadata, created_at, updated_at, last_modified, server_created_at)
                    VALUES
                        (%(id)s, %(timestamp)s, %(duration)s, %(reason)s, %(notes)s, %(provider_id)s, %(clinic_id)s, %(patient_id)s, %(user_id)s, %(status)s, %(current_visit_id)s, %(fufilled_visit_id)s, %(metadata)s, %(created_at)s, %(updated_at)s, %(last_modified)s, %(server_created_at)s)   
                    ON CONFLICT (id) DO UPDATE
                    SET
                        timestamp=EXCLUDED.appointment_timestamp
                        duration=EXCLUDED.duration,  
                        reason=EXCLUDED.reason, 
                        notes=EXCLUDED.notes, 
                        provider_id=EXCLUDED.provider_id, 
                        clinic_id=EXCLUDED.clinic_id, 
                        patient_id=EXCLUDED.patient_id, 
                        user_id=EXCLUDED.user_id,
                        status=EXCLUDED.status, 
                        current_visit_id=EXCLUDED.current_visit_id
                        fufilled_visit_id=EXCLUDED.fufilled_visit_id
                        metadata=EXCLUDED.metadata
                        created_at=EXCLUDED.created_at
                        updated_at=EXCLUDED.updated_at 
                        last_modified=EXCLUDED.last_modified
                        server_created_at=EXCLUDED.server_created_at
                    """,
                    appointment
                )

            for id in deltadata.deleted:
                cur.execute(
                    """UPDATE appointments SET is_deleted=true, deleted_at=%s WHERE id=%s;""",
                        (last_pushed_at, id)
                )