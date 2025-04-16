from __future__ import annotations
from collections import defaultdict
import logging

from psycopg import Connection
from psycopg.cursor import Cursor

from hikmahealth import sync
from hikmahealth.entity import core, fields, helpers
from .sync import (
    SyncToClient,
    SyncToServer,
)

from datetime import datetime
from hikmahealth.utils.datetime import utc

from datetime import date


import itertools

from hikmahealth.server.client import db
from typing import Any

from psycopg.rows import class_row, dict_row
import dataclasses
import json
from urllib import parse as urlparse

from hikmahealth.utils.misc import is_valid_uuid, safe_json_dumps
from hikmahealth.entity.helpers import SimpleCRUD, get_from_dict
import uuid


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
class Patient(SyncToClient, SyncToServer, helpers.SimpleCRUD):
    TABLE_NAME = 'patients'

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

    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

    @classmethod
    def create_from_delta(cls, ctx, cur: Cursor, data: dict):
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
            data,
        )

    @classmethod
    def update_from_delta(cls, ctx, cur: Cursor, data: dict):
        return cls.create_from_delta(ctx, cur, data)

    @classmethod
    def delete_from_delta(cls, ctx, cur: Cursor, id: str):
        cur.execute(
            """INSERT INTO patients
                  (id, is_deleted, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified, deleted_at)
                VALUES
                  (%s::uuid, true, '', '', NULL, '', '', '', '', '', '{}', NULL, '', NULL, NULL, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET is_deleted = true,
                    deleted_at = EXCLUDED.deleted_at,
                    updated_at = EXCLUDED.updated_at,
                    last_modified = EXCLUDED.last_modified;
            """,
            (id, utc.now(), utc.now(), utc.now(), utc.now()),
        )

        # Soft delete patient_additional_attributes for deleted patients
        cur.execute(
            """
            UPDATE patient_additional_attributes
            SET is_deleted = true,
                deleted_at = %s,
                updated_at = %s,
                last_modified = %s
            WHERE patient_id = %s::uuid;
            """,
            (utc.now(), utc.now(), utc.now(), id),
        )

        # Soft delete visits for deleted patients
        cur.execute(
            """
            UPDATE visits
            SET is_deleted = true,
                deleted_at = %s,
                updated_at = %s,
                last_modified = %s
            WHERE patient_id = %s::uuid;
            """,
            (utc.now(), utc.now(), utc.now(), id),
        )

        # Soft delete events for deleted patients
        cur.execute(
            """
            UPDATE events
            SET is_deleted = true,
                deleted_at = %s,
                updated_at = %s,
                last_modified = %s
            WHERE patient_id = %s::uuid;
            """,
            (utc.now(), utc.now(), utc.now(), id),
        )

        # Soft delete appointments for deleted patients
        cur.execute(
            """
            UPDATE appointments
            SET is_deleted = true,
                deleted_at = %s,
                updated_at = %s,
                last_modified = %s
            WHERE patient_id = %s::uuid;
            """,
            (utc.now(), utc.now(), utc.now(), id),
        )

    @classmethod
    def transform_delta(cls, ctx, action: str, data: Any):
        if action == sync.ACTION_CREATE or action == sync.ACTION_UPDATE:
            patient = dict(data)

            additional_data = patient.get('additional_data', None)
            # Handle additional_data
            if additional_data is None or additional_data == '':
                additional_data = '{}'  # Empty JSON object
            elif isinstance(additional_data, (dict, list)):
                additional_data = safe_json_dumps(additional_data)
            elif isinstance(patient.get('additional_data', None), str):
                try:
                    json.loads(additional_data)
                except json.JSONDecodeError:
                    # Empty JSON object if invalid
                    additional_data = '{}'

            patient.update(
                additional_data=additional_data,
                created_at=helpers.get_from_dict(
                    patient, 'created_at', utc.from_unixtimestamp
                ),
                updated_at=helpers.get_from_dict(
                    patient, 'updated_at', utc.from_unixtimestamp
                ),
                image_timestamp=helpers.get_from_dict(
                    patient, 'image_timestamp', utc.from_unixtimestamp
                ),
                photo_url='',
                last_modified=utc.now(),
            )

            return patient

    # @classmethod
    # def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
    #     """Applies the delta changes pushed by the client to this server database.

    #     NOTE: might want to have `DeltaData` as only input and add `last_pushed_at` to deleted"""
    #     with conn.cursor() as cur:
    #         # performs upserts (insert + update when existing)
    #         for row in itertools.chain(deltadata.created, deltadata.updated):
    #             patient = dict(row)

    #             # Handle additional_data
    #             if (
    #                 patient.get('additional_data', None) is None
    #                 or patient['additional_data'] == ''
    #             ):
    #                 patient['additional_data'] = '{}'  # Empty JSON object
    #             elif isinstance(patient.get('additional_data', None), (dict, list)):
    #                 patient['additional_data'] = json.dumps(patient['additional_data'])
    #             elif isinstance(patient.get('additional_data', None), str):
    #                 try:
    #                     json.loads(patient['additional_data'])
    #                 except json.JSONDecodeError:
    #                     # Empty JSON object if invalid
    #                     patient['additional_data'] = '{}'

    #             patient.update(
    #                 created_at=utc.from_unixtimestamp(patient['created_at']),
    #                 updated_at=utc.from_unixtimestamp(patient['updated_at']),
    #                 image_timestamp=utc.from_unixtimestamp(patient['image_timestamp'])
    #                 if 'image_timestamp' in patient
    #                 else None,
    #                 photo_url='',
    #                 last_modified=utc.now(),
    #             )

    #             cur.execute(
    #                 """INSERT INTO patients
    #                       (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified)
    #                     VALUES
    #                       (%(id)s, %(given_name)s, %(surname)s, %(date_of_birth)s, %(citizenship)s, %(hometown)s, %(sex)s, %(phone)s, %(camp)s, %(additional_data)s, %(image_timestamp)s, %(photo_url)s, %(government_id)s, %(external_patient_id)s, %(created_at)s, %(updated_at)s, %(last_modified)s)
    #                     ON CONFLICT (id) DO UPDATE
    #                     SET given_name = EXCLUDED.given_name,
    #                         surname = EXCLUDED.surname,
    #                         date_of_birth = EXCLUDED.date_of_birth,
    #                         citizenship = EXCLUDED.citizenship,
    #                         hometown = EXCLUDED.hometown,
    #                         sex = EXCLUDED.sex,
    #                         phone = EXCLUDED.phone,
    #                         camp = EXCLUDED.camp,
    #                         additional_data = EXCLUDED.additional_data,
    #                         government_id = EXCLUDED.government_id,
    #                         external_patient_id = EXCLUDED.external_patient_id,
    #                         created_at = EXCLUDED.created_at,
    #                         updated_at = EXCLUDED.updated_at,
    #                         last_modified = EXCLUDED.last_modified;
    #                 """,
    #                 patient,
    #             )

    #         for id in deltadata.deleted:
    #             # Upsert delete patient record
    #             cur.execute(
    #                 """INSERT INTO patients
    #                       (id, is_deleted, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified, deleted_at)
    #                     VALUES
    #                       (%s::uuid, true, '', '', NULL, '', '', '', '', '', '{}', NULL, '', NULL, NULL, %s, %s, %s, %s)
    #                     ON CONFLICT (id) DO UPDATE
    #                     SET is_deleted = true,
    #                         deleted_at = EXCLUDED.deleted_at,
    #                         updated_at = EXCLUDED.updated_at,
    #                         last_modified = EXCLUDED.last_modified;
    #                 """,
    #                 (id, utc.now(), utc.now(), utc.now(), utc.now()),
    #             )

    #             # Soft delete patient_additional_attributes for deleted patients
    #             cur.execute(
    #                 """
    #                 UPDATE patient_additional_attributes
    #                 SET is_deleted = true,
    #                     deleted_at = %s,
    #                     updated_at = %s,
    #                     last_modified = %s
    #                 WHERE patient_id = %s::uuid;
    #                 """,
    #                 (utc.now(), utc.now(), utc.now(), id),
    #             )

    #             # Soft delete visits for deleted patients
    #             cur.execute(
    #                 """
    #                 UPDATE visits
    #                 SET is_deleted = true,
    #                     deleted_at = %s,
    #                     updated_at = %s,
    #                     last_modified = %s
    #                 WHERE patient_id = %s::uuid;
    #                 """,
    #                 (utc.now(), utc.now(), utc.now(), id),
    #             )

    #             # Soft delete events for deleted patients
    #             cur.execute(
    #                 """
    #                 UPDATE events
    #                 SET is_deleted = true,
    #                     deleted_at = %s,
    #                     updated_at = %s,
    #                     last_modified = %s
    #                 WHERE patient_id = %s::uuid;
    #                 """,
    #                 (utc.now(), utc.now(), utc.now(), id),
    #             )

    #             # Soft delete appointments for deleted patients
    #             cur.execute(
    #                 """
    #                 UPDATE appointments
    #                 SET is_deleted = true,
    #                     deleted_at = %s,
    #                     updated_at = %s,
    #                     last_modified = %s
    #                 WHERE patient_id = %s::uuid;
    #                 """,
    #                 (utc.now(), utc.now(), utc.now(), id),
    #             )

    @classmethod
    def get_column_names(cls):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                q = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'patients'
                    ORDER BY ordinal_position
                """
                cur.execute(q)
                return [row[0] for row in cur.fetchall()]

    @classmethod
    def filter_valid_colums(cls, columns: list[str]) -> list[str]:
        valid_columns = cls.get_column_names()
        return [column for column in columns if column in valid_columns]

    @classmethod
    def get_all_with_attributes(cls, count=None):
        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                query = """
                SELECT
                    p.*,
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
                FROM patients p
                LEFT JOIN patient_additional_attributes pa ON p.id = pa.patient_id
                WHERE p.is_deleted = false
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
                if count is not None:
                    query += f' LIMIT {count}'
                cur.execute(query)
                patients = cur.fetchall()

                for patient in patients:
                    # Convert additional_attributes from JSON string to dict
                    # patient['additional_attributes'] = json.loads(
                    #     patient['additional_attributes'])

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
                        patient['date_of_birth'] = patient['date_of_birth'].isoformat()

                return patients

    @classmethod
    def search(cls, query, conn: Connection):
        # Only supporting search by either first or surname
        # TODO: add support for text searching some of the attributes
        with conn.cursor(row_factory=dict_row) as cur:
            search_query = """
                SELECT
                    p.*,
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
                FROM patients p
                LEFT JOIN patient_additional_attributes pa ON p.id = pa.patient_id
                WHERE p.is_deleted = false
                AND (LOWER(p.given_name) LIKE LOWER(%s) OR LOWER(p.surname) LIKE LOWER(%s))
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            search_pattern = f'%{query}%'
            cur.execute(search_query, (search_pattern, search_pattern))
            patients = cur.fetchall()

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
                    patient['date_of_birth'] = patient['date_of_birth'].isoformat()

            return patients


@core.dataentity
class PatientAttribute(SyncToClient, SyncToServer):
    TABLE_NAME = 'patient_additional_attributes'

    @classmethod
    def transform_delta(cls, ctx, action: str, data: Any):
        if action == sync.ACTION_CREATE or action == sync.ACTION_UPDATE:
            pattr = dict(data)
            pattr.update(
                date_value=get_from_dict(pattr, 'date_value', utc.from_unixtimestamp),
                created_at=get_from_dict(pattr, 'created_at', utc.from_unixtimestamp),
                updated_at=get_from_dict(pattr, 'updated_at', utc.from_unixtimestamp),
                metadata=safe_json_dumps(pattr.get('metadata')),
            )

            return pattr

    @classmethod
    def create_from_delta(cls, ctx, cur: Cursor, data: dict):
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
            data,
        )

    @classmethod
    def update_from_delta(cls, ctx, cur: Cursor, data: dict):
        return cls.create_from_delta(ctx, cur, data)

    @classmethod
    def delete_from_delta(cls, ctx, cur: Cursor, id: str):
        cur.execute(
            """UPDATE patient_additional_attributes SET is_deleted=true, deleted_at=%s WHERE id = %s::uuid;""",
            (ctx.last_pushed_at, id),
        )


@core.dataentity
class Event(SyncToClient, SyncToServer):
    TABLE_NAME = 'events'

    id: str
    patient_id: str | None = None
    visit_id: str | None = None
    form_id: str | None = None
    event_type: str | None = None
    form_data: dict | None = None
    metadata: dict | None = None

    @classmethod
    def transform_delta(cls, ctx, action: str, data: Any):
        if action == sync.ACTION_CREATE or action == sync.ACTION_UPDATE:
            event = dict(data)

            event.update(
                created_at=get_from_dict(event, 'created_at', utc.from_unixtimestamp),
                updated_at=get_from_dict(event, 'updated_at', utc.from_unixtimestamp),
                metadata=get_from_dict(event, 'metadata', safe_json_dumps, '{}'),
                form_data=get_from_dict(event, 'form_data', safe_json_dumps, '{}'),
                visit_id=data.get('visit_id'),
                patient_id=data.get('patient_id'),
                last_modified=data.get('last_modified', utc.now()),
                form_id=data.get('form_id'),
                event_type=data.get('event_type'),
            )

            return event

    @classmethod
    def create_from_delta(cls, ctx, cur: Cursor, data: dict):
        assert data['id'] is not None, "missing 'id' from the event data"
        # NOTE: might need to delete the patient_id
        assert data['patient_id'] is not None
        patient_id = data['patient_id']
        patient_exists = False

        # --------------------------------------
        # Check if patient exists
        # Upsert then if not
        cur.execute(
            'SELECT EXISTS(SELECT 1 FROM patients WHERE id = %s)',
            (patient_id,),
        )
        d = cur.fetchone()
        if d is not None:
            patient_exists = d[0]

        if not patient_exists:
            # We are choosing to create patients dynamically here if they don't exist.
            # We can also choose to skip events for non-existent patients.
            placeholder_metadata = json.dumps({
                'artificially_created': True,
                'created_from': 'server_event_creation',
                'original_event_id': data['id'],
            })
            cur.execute(
                """
                INSERT INTO patients (id, given_name, surname, is_deleted, deleted_at, created_at, updated_at, metadata)
                VALUES (%s, '', '', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
                ON CONFLICT (id) DO NOTHING
            """,
                (patient_id, placeholder_metadata),
            )

            ctx.conn.commit()
        # --------------------------------------

        vid = data.get('visit_id')
        if vid is not None:
            exists = False

            cur.execute(
                """
                SELECT EXISTS(SELECT 1 FROM visits WHERE id = %s)
                """,
                (vid,),
            )

            d = cur.fetchone()
            if d is not None:
                exists = d[0]

            if not exists:
                logging.warning(
                    f'Event {data["id"]} references non-existent visit {
                        data["visit_id"]
                    }. Setting visit_id to None.'
                )
                print(
                    f'REVIEWER WARNING: Event {
                        data["id"]
                    } references non-existent visit {
                        data["visit_id"]
                    }. visit_id will be set to None.'
                )

                data['visit_id'] = None

        # --------------------------------------

        fid = data['form_id']
        if fid is not None:
            exists = False

            cur.execute(
                """
                SELECT EXISTS(SELECT 1 FROM event_forms WHERE id = %s)
                """,
                (fid,),
            )

            d = cur.fetchone()
            if d is not None:
                exists = d[0]

            if not exists:
                logging.warning(
                    f'Event {data["id"]} references non-existent visit {
                        data["form_id"]
                    }. Setting form_id to None.'
                )
                print(
                    f'REVIEWER WARNING: Event {
                        data["id"]
                    } references non-existent visit {
                        data["form_id"]
                    }. visit_id will be set to None.'
                )

                data['form_id'] = None

        # AT THIS POINT: We know that the patient must exist.
        # AT THIS POINT: We know that the visit may exist.
        # AT THIS POINT: We know that the form may exist.
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
            data,
        )

    @classmethod
    def update_from_delta(cls, ctx, cur: Cursor, data: dict):
        return cls.create_from_delta(ctx, cur, data)

    @classmethod
    def delete_from_delta(cls, ctx, cur: Cursor, id: str):
        cur.execute(
            """
            UPDATE events
            SET is_deleted = true, deleted_at = %s
            WHERE id = %s
            """,
            (ctx.last_pushed_at, id),
        )

    # @classmethod
    # def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
    #     with conn.cursor() as cur:
    #         try:
    #             # `cur.executemany` can be used instead
    #             for row in itertools.chain(deltadata.created, deltadata.updated):
    #                 event = dict(row)
    #                 event.update(
    #                     created_at=utc.from_unixtimestamp(event['created_at']),
    #                     updated_at=utc.from_unixtimestamp(event['updated_at']),
    #                     metadata=json.dumps(event['metadata']),
    #                 )

    #                 # Check if patient exists
    #                 cur.execute(
    #                     'SELECT EXISTS(SELECT 1 FROM patients WHERE id = %s)',
    #                     (event['patient_id'],),
    #                 )
    #                 patient_exists = cur.fetchone()[0]

    #                 if not patient_exists:
    #                     # Log out that there is no patient with and event_id. warn reviewer
    #                     logging.warning(
    #                         f'Event {event["id"]} references non-existent patient {
    #                             event["patient_id"]
    #                         }. Creating placeholder patient, marked as artificially created and deleted.'
    #                     )
    #                     print(
    #                         f'REVIEWER WARNING: Event {
    #                             event["id"]
    #                         } references non-existent patient {
    #                             event["patient_id"]
    #                         }. A placeholder patient will be created.'
    #                     )

    #                     # We are choosing to create patients dynamically here if they don't exist.
    #                     # We can also choose to skip events for non-existent patients.
    #                     placeholder_metadata = json.dumps({
    #                         'artificially_created': True,
    #                         'created_from': 'server_event_creation',
    #                         'original_event_id': event['id'],
    #                     })
    #                     cur.execute(
    #                         """
    #                         INSERT INTO patients (id, given_name, surname, is_deleted, deleted_at, created_at, updated_at, metadata)
    #                         VALUES (%s, '', '', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
    #                         ON CONFLICT (id) DO NOTHING
    #                     """,
    #                         (event['patient_id'], placeholder_metadata),
    #                     )

    #                 # Verify that the visit exists
    #                 if event.get('visit_id'):
    #                     # If the visit_id is not valid, set it to None
    #                     cur.execute(
    #                         """
    #                         SELECT EXISTS(SELECT 1 FROM visits WHERE id = %s)
    #                         """,
    #                         (event['visit_id'],),
    #                     )
    #                     form_exists = cur.fetchone()[0]

    #                     if not form_exists:
    #                         logging.warning(
    #                             f'Event {event["id"]} references non-existent visit {
    #                                 event["visit_id"]
    #                             }. Setting visit_id to None.'
    #                         )
    #                         print(
    #                             f'REVIEWER WARNING: Event {
    #                                 event["id"]
    #                             } references non-existent visit {
    #                                 event["visit_id"]
    #                             }. visit_id will be set to None.'
    #                         )
    #                         event['visit_id'] = None
    #                 else:
    #                     # If the visit_id is not valid, set it to None
    #                     event['visit_id'] = None

    #                 # Verify that a form exists
    #                 if event.get('form_id'):
    #                     # If the visit_id is not valid, set it to None
    #                     cur.execute(
    #                         """
    #                         SELECT EXISTS(SELECT 1 FROM event_forms WHERE id = %s)
    #                         """,
    #                         (event['form_id'],),
    #                     )
    #                     form_exists = cur.fetchone()[0]

    #                     if not form_exists:
    #                         logging.warning(
    #                             f'Event {event["id"]} references non-existent form {
    #                                 event["form_id"]
    #                             }. Setting form_id to None.'
    #                         )
    #                         print(
    #                             f'REVIEWER WARNING: Event {
    #                                 event["id"]
    #                             } references non-existent form {
    #                                 event["form_id"]
    #                             }. form_id will be set to None.'
    #                         )
    #                         event['form_id'] = None
    #                 else:
    #                     # If the visit_id is not valid, set it to None
    #                     event['form_id'] = None

    #                 # AT THIS POINT: We know that the patient must exist.
    #                 # AT THIS POINT: We know that the visit must exist or is None.
    #                 # AT THIS POINT: We know that the form must exist or is None.
    #                 cur.execute(
    #                     """
    #                     INSERT INTO events
    #                     (id, patient_id, form_id, visit_id, event_type, form_data, metadata, is_deleted, created_at, updated_at, last_modified)
    #                     VALUES
    #                     (%(id)s, %(patient_id)s, %(form_id)s, %(visit_id)s, %(event_type)s, %(form_data)s, %(metadata)s, false, %(created_at)s, %(updated_at)s, current_timestamp)
    #                     ON CONFLICT (id) DO UPDATE
    #                     SET patient_id=EXCLUDED.patient_id,
    #                         form_id=EXCLUDED.form_id,
    #                         visit_id=EXCLUDED.visit_id,
    #                         event_type=EXCLUDED.event_type,
    #                         form_data=EXCLUDED.form_data,
    #                         metadata=EXCLUDED.metadata,
    #                         created_at=EXCLUDED.created_at,
    #                         updated_at=EXCLUDED.updated_at,
    #                         last_modified=EXCLUDED.last_modified;
    #                     """,
    #                     event,
    #                 )
    #             for id in deltadata.deleted:
    #                 # First, get the event data
    #                 # cur.execute(
    #                 #     """
    #                 #     SELECT id, patient_id, visit_id, form_id, event_type, form_data, metadata, created_at
    #                 #     FROM events
    #                 #     WHERE id = %s
    #                 #     """,
    #                 #     (id,),
    #                 # )
    #                 # event_data = cur.fetchone()

    #                 # if event_data:
    #                 #     d_visit_id = event_data[2]
    #                 #     d_id = event_data[0]

    #                 #     # d_form_id = event_data[3]

    #                 #     if d_visit_id:
    #                 #         # Check if the visit exists
    #                 #         cur.execute(
    #                 #             """
    #                 #             SELECT id FROM visits WHERE id = %s
    #                 #             """,
    #                 #             (d_visit_id,),
    #                 #         )
    #                 #         visit_exists = cur.fetchone()

    #                 #         if not visit_exists:
    #                 #             # If the visit doesn't exist, warn the user
    #                 #             logging.warning(
    #                 #                 f'Event {d_id} references non-existent visit {
    #                 #                     d_visit_id
    #                 #                 }. Creating placeholder visit, marked as artificially created and deleted.'
    #                 #             )
    #                 #             print(
    #                 #                 f'REVIEWER WARNING: Event {
    #                 #                     d_id
    #                 #                 } references non-existent visit {
    #                 #                     d_visit_id
    #                 #                 }. A placeholder visit will be created.'
    #                 #             )

    #                 # Finally, soft delete the event
    #                 cur.execute(
    #                     """
    #                     UPDATE events
    #                     SET is_deleted = true, deleted_at = %s
    #                     WHERE id = %s
    #                     """,
    #                     (last_pushed_at, id),
    #                 )
    #             # for id in deltadata.deleted:
    #             #     cur.execute(
    #             #         """UPDATE events SET is_deleted=true, deleted_at=%s WHERE id = %s;""",
    #             #         (last_pushed_at, id)
    #             #     )

    #             # Commit changes
    #             conn.commit()
    #         except Exception as e:
    #             print(f'Event Errors: {str(e)}')
    #             conn.rollback()
    #             raise e

    @classmethod
    def get_events_by_form_id(cls, form_id: str, start_date: str, end_date: str):
        """Returns all the formated events as a single table that can be easily rendered"""

        where_clause = []
        if start_date is not None:
            start_date = utc.from_datetime(
                datetime.fromisoformat(urlparse.unquote(start_date))
            )

            where_clause.append('e.created_at >= %(start_date)s')

        if end_date is not None:
            end_date = utc.from_datetime(
                datetime.fromisoformat(urlparse.unquote(end_date))
            )

            where_clause.append('e.created_at <= %(end_date)s')

        events = []
        query = """
        SELECT
            events.id,
            events.patient_id,
            events.visit_id,
            events.form_id,
            events.event_type,
            events.form_data,
            events.metadata,
            events.is_deleted,
            events.created_at,
            events.updated_at,
            jsonb_build_object(
                'id', p.id,
                'given_name', p.given_name,
                'surname', p.surname,
                'date_of_birth', p.date_of_birth,
                'sex', p.sex,
                'camp', p.camp,
                'citizenship', p.citizenship,
                'hometown', p.hometown,
                'phone', p.phone,
                'additional_data', p.additional_data,
                'government_id', p.government_id,
                'external_patient_id', p.external_patient_id,
                'created_at', p.created_at,
                'updated_at', p.updated_at,
                'additional_attributes', COALESCE(json_object_agg(
                    pa.attribute_id,
                    json_build_object(
                        'attribute', pa.attribute,
                        'number_value', pa.number_value,
                        'string_value', pa.string_value,
                        'date_value', pa.date_value,
                        'boolean_value', pa.boolean_value
                    )
                ) FILTER (WHERE pa.attribute_id IS NOT NULL), '{}'::json)
            ) AS patient
        FROM events
        JOIN patients p ON events.patient_id = p.id
        LEFT JOIN patient_additional_attributes pa ON p.id = pa.patient_id
        WHERE events.form_id = %s
        AND events.is_deleted = false
        AND events.created_at >= %s
        AND events.created_at <= %s
        AND p.is_deleted = false
        GROUP BY events.id, events.patient_id, events.visit_id, events.form_id, events.event_type, events.form_data, events.metadata, events.is_deleted, events.created_at, events.updated_at, p.id
        """

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(query, (form_id, start_date, end_date))

                    for entry in cur.fetchall():
                        patient = entry[10]

                        events.append({
                            'id': entry[0],
                            'patientId': entry[1],
                            'visitId': entry[2],
                            'formId': entry[3],
                            'eventType': entry[4],
                            'formData': entry[5],
                            'metadata': entry[6],
                            'isDeleted': entry[7],
                            'createdAt': entry[8],
                            'updatedAt': entry[9],
                            'patient': patient,
                        })
                except Exception as e:
                    print('Error while updating the patient registration form: ', e)
                    raise e

            return events


@core.dataentity
class Visit(SyncToClient, SyncToServer, helpers.SimpleCRUD):
    TABLE_NAME = 'visits'

    check_in_timestamp: fields.UTCDateTime
    clinic_id: str
    patient_id: str
    provider_id: str
    provider_name: str
    id: str
    metadata: dict | None = None
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

    @classmethod
    def create_from_delta(cls, ctx, cur: Cursor, data: dict):
        """Writes the data to the database."""
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
            data,
        )

    @classmethod
    def update_from_delta(cls, ctx, cur, data):
        return cls.create_from_delta(ctx, cur, data)

    @classmethod
    def delete_from_delta(cls, ctx, cur: Cursor, id: str):
        now = utc.now()

        # Soft delete visit and related records
        cur.execute(
            """
            UPDATE visits
            SET is_deleted = true,
                deleted_at = %s,
                updated_at = %s,
                last_modified = %s
            WHERE id = %s::uuid
            RETURNING id;
            """,
            (now, now, now, id),
        )

        updated_visit_ids = [row[0] for row in cur.fetchall()]

        if updated_visit_ids:
            cur.execute(
                """
                UPDATE events
                SET is_deleted = true,
                    deleted_at = %s,
                    updated_at = %s,
                    last_modified = %s
                WHERE visit_id = ANY(%s);
                """,
                (now, now, now, updated_visit_ids),
            )

            cur.execute(
                """
                UPDATE appointments
                SET is_deleted = true,
                    deleted_at = %s,
                    updated_at = %s,
                    last_modified = %s
                WHERE current_visit_id = ANY(%s) OR fulfilled_visit_id = ANY(%s);
                """,
                (now, now, now, updated_visit_ids, updated_visit_ids),
            )

            # TODO: Soft delete prescriptions for deleted visits
            cur.execute(
                """
                UPDATE prescriptions
                SET is_deleted = true,
                    deleted_at = %s,
                    updated_at = %s,
                    last_modified = %s
                WHERE visit_id = ANY(%s);
                """,
                (now, now, now, updated_visit_ids),
            )

        return now

    @classmethod
    def transform_delta(cls, ctx, action: str, data: Any):
        if action == sync.ACTION_CREATE or action == sync.ACTION_UPDATE:
            visit = dict(data)
            visit.update(
                check_in_timestamp=helpers.get_from_dict(
                    visit, 'check_in_timestamp', utc.from_unixtimestamp
                ),
                created_at=helpers.get_from_dict(
                    visit, 'created_at', utc.from_unixtimestamp
                ),
                updated_at=helpers.get_from_dict(
                    visit, 'updated_at', utc.from_unixtimestamp
                ),
                metadata=helpers.get_from_dict(visit, 'metadata', safe_json_dumps),
                last_modified=utc.now(),
            )
            return visit


@core.dataentity
class Clinic(SyncToClient):
    TABLE_NAME = 'clinics'

    id: str
    name: str | None = None
    address: str | None = None
    metadata: dict | None = None
    attributes: list | None = None

    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)


@core.dataentity
class PatientRegistrationForm(SyncToClient, helpers.SimpleCRUD):
    TABLE_NAME = 'patient_registration_forms'

    id: str
    name: str
    fields: str
    metadata: str

    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)


@core.dataentity
class EventForm(SyncToClient, helpers.SimpleCRUD):
    TABLE_NAME = 'event_forms'

    id: str
    name: str
    description: str

    metadata: dict
    form_fields: fields.JSON = fields.JSON(default_factory=tuple)
    # metadata: fields.JSON = fields.JSON(default_factory=dict)

    is_editable: bool | None = None
    is_snapshot_form: bool | None = None
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)


@core.dataentity
class StringId(SyncToClient):
    TABLE_NAME = 'string_ids'


@core.dataentity
class StringContent(SyncToClient):
    TABLE_NAME = 'string_content'


@core.dataentity
class Appointment(SyncToClient, SyncToServer):
    TABLE_NAME = 'appointments'

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
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    last_modified: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    server_created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

    @classmethod
    def transform_delta(cls, ctx, action: str, data: Any):
        if action == sync.ACTION_CREATE or action == sync.ACTION_UPDATE:
            appointment = cls(id=data['id']).to_dict() | dict(data)
            appointment.update(
                notes=data.get('notes', ''),
                reason=data.get('reason', ''),
                timestamp=get_from_dict(
                    appointment, 'timestamp', utc.from_unixtimestamp
                ),
                created_at=get_from_dict(
                    appointment, 'created_at', utc.from_unixtimestamp
                ),
                updated_at=get_from_dict(
                    appointment, 'updated_at', utc.from_unixtimestamp
                ),
                metadata=safe_json_dumps(appointment.get('metadata')),
                last_modified=utc.now(),
                clinic_id=data.get('clinic_id'),
                user_id=data.get('user_id'),
                provider_name=data.get('provider_name'),
                is_deleted=data.get('is_deleted', False),
                deleted_at=get_from_dict(
                    appointment, 'deleted_at', utc.from_unixtimestamp
                ),
            )

            if action == sync.ACTION_CREATE:
                appointment.update(
                    server_created_at=utc.now(),
                )

            provider_id = appointment.get('provider_id')
            if not provider_id or not is_valid_uuid(provider_id):
                appointment['provider_id'] = None

            patient_id = appointment.get('patient_id')
            if not patient_id or not is_valid_uuid(patient_id):
                appointment['patient_id'] = None

            current_visit_id = appointment.get('current_visit_id')
            if not current_visit_id or not is_valid_uuid(current_visit_id):
                appointment['current_visit_id'] = None

            fulfilled_visit_id = appointment.get('fulfilled_visit_id')
            if not fulfilled_visit_id or not is_valid_uuid(fulfilled_visit_id):
                appointment['fulfilled_visit_id'] = None

            return appointment

    @classmethod
    def create_from_delta(cls, ctx, cur: Cursor, data: dict):
        assert data['id'] is not None

        if data.get('patient_id') is not None:
            data['patient_id'] = str(uuid.uuid1())
            insert_placeholder_patient(ctx.conn, data['patient_id'], True)

        assert data['patient_id'] is not None

        with_server_metadata = {
            'artificially_created': True,
            'created_from': 'server_appointment_creation',
            'original_appointment_id': data.get('id', ''),
        }
        metadataobj = json.loads(data['metadata'])
        if metadataobj is not None:
            with_server_metadata = metadataobj | with_server_metadata

        curr_vid = data.get('current_visit_id')
        if curr_vid is not None:
            visit_exists = row_exists('visits', curr_vid)

            if not visit_exists:
                data['current_visit_id'] = curr_vid

        # still empty set new ID
        if data.get('current_visit_id') is not None:
            print(f'Invalid current_visit_id for appointment: {data.get("id")}')
            data['current_visit_id'] = str(uuid.uuid1())

        upsert_visit(
            data['current_visit_id'],
            data['patient_id'],
            data.get('clinic_id'),
            data.get('user_id'),
            data.get('provider_name', ''),
            data.get('check_in_timestamp', utc.now()),
            with_server_metadata,
        )

        fulfilled_vid = data.get('fulfilled_visit_id')
        if fulfilled_vid is not None:
            visit_exists = row_exists('visits', fulfilled_vid)

            if not visit_exists:
                data['fulfilled_visit_id'] = fulfilled_vid
            else:
                print(f'Invalid fulfilled_visit_id for appointment: {data.get("id")}')
                data['fulfilled_visit_id'] = str(uuid.uuid1())

            upsert_visit(
                data['fulfilled_visit_id'],
                data['patient_id'],
                data.get('clinic_id'),
                data.get('user_id'),
                data.get('provider_name', ''),
                data.get('check_in_timestamp', utc.now()),
                with_server_metadata,
            )

        cur.execute(
            """
            INSERT INTO appointments
                (id, timestamp, duration, reason, notes, provider_id, clinic_id, patient_id, user_id, status, current_visit_id, fulfilled_visit_id, metadata, created_at, updated_at, last_modified, is_deleted, server_created_at, deleted_at)
            VALUES
                (%(id)s, %(timestamp)s, %(duration)s, %(reason)s, %(notes)s, %(provider_id)s, %(clinic_id)s, %(patient_id)s, %(user_id)s, %(status)s, %(current_visit_id)s, %(fulfilled_visit_id)s, %(metadata)s, COALESCE(%(created_at)s, CURRENT_TIMESTAMP), COALESCE(%(updated_at)s, CURRENT_TIMESTAMP), %(last_modified)s, %(is_deleted)s, %(server_created_at)s, %(deleted_at)s)
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
                is_deleted=EXCLUDED.is_deleted,
                deleted_at=EXCLUDED.deleted_at
            """,
            data,
        )

    @classmethod
    def update_from_delta(cls, ctx, cur: Cursor, data: dict):
        return cls.create_from_delta(ctx, cur, data)

    @classmethod
    def delete_from_delta(cls, ctx, cur: Cursor, id: str):
        # Not making 'cancelled' appointments 'deleted' on purpose. we need to sync them
        # Update the appointment to mark it as deleted
        cur.execute(
            """
            UPDATE appointments
            SET is_deleted = true, deleted_at = COALESCE(%s, CURRENT_TIMESTAMP)
            WHERE id = %s
            """,
            (ctx.last_pushed_at, id),
        )

    # @classmethod
    # def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
    #     with conn.cursor() as cur:
    #         try:
    #             # TODO: `cur.executemany` can be used instead
    #             print(f'Applying delta changes for appointments')
    #             for appointment in itertools.chain(
    #                 deltadata.created, deltadata.updated
    #             ):
    #                 appointment = dict(appointment)
    #                 appointment.update(
    #                     timestamp=utc.from_unixtimestamp(appointment.get('timestamp')),
    #                     created_at=utc.from_unixtimestamp(
    #                         appointment.get('created_at')
    #                     ),
    #                     updated_at=utc.from_unixtimestamp(
    #                         appointment.get('updated_at')
    #                     ),
    #                     server_created_at=utc.now(),
    #                     # metadata=json.dumps(appointment.get("metadata", {})),
    #                     metadata=safe_json_dumps(appointment.get('metadata', {})),
    #                     last_modified=utc.now(),
    #                 )

    #                 provider_id = appointment.get('provider_id')
    #                 patient_id = appointment.get('patient_id')
    #                 clinic_id = appointment.get('clinic_id')
    #                 user_id = appointment.get('user_id')

    #                 # Set provider_id to None if it's not present, empty, or an invalid UUID
    #                 if not provider_id or not is_valid_uuid(provider_id):
    #                     print(
    #                         f'Invalid provider_id for appointment: {appointment["id"]}'
    #                     )
    #                     appointment['provider_id'] = None

    #                 if not patient_id or not is_valid_uuid(patient_id):
    #                     print(
    #                         f'Invalid patient_id for appointment: {appointment["id"]}'
    #                     )
    #                     # Patient id is not valid. Create a placeholder patient.
    #                     insert_placeholder_patient(conn, patient_id, True)

    #                 server_created_metadata = {
    #                     'artificially_created': True,
    #                     'created_from': 'server_appointment_creation',
    #                     'original_appointment_id': appointment.get('id', ''),
    #                 }

    #                 if appointment.get('current_visit_id') and is_valid_uuid(
    #                     appointment.get('current_visit_id')
    #                 ):
    #                     visit_exists = row_exists(
    #                         'visits', appointment.get('current_visit_id')
    #                     )
    #                     if not visit_exists:
    #                         current_visit_id = upsert_visit(
    #                             appointment.get('current_visit_id'),
    #                             patient_id,
    #                             clinic_id,
    #                             user_id,
    #                             appointment.get('provider_name', ''),
    #                             appointment.get('check_in_timestamp', utc.now()),
    #                             {
    #                                 **appointment.get('metadata', {}),
    #                                 **server_created_metadata,
    #                             },
    #                         )
    #                         appointment['current_visit_id'] = current_visit_id
    #                 else:
    #                     print(
    #                         f'Invalid current_visit_id for appointment: {
    #                             appointment.get("current_visit_id")
    #                         }'
    #                     )
    #                     # If there is no valid current_visit_id create a new visit
    #                     current_visit_id = upsert_visit(
    #                         str(uuid.uuid1()),
    #                         patient_id,
    #                         clinic_id,
    #                         user_id,
    #                         appointment.get('provider_name', ''),
    #                         appointment.get('check_in_timestamp', utc.now()),
    #                         {
    #                             **appointment.get('metadata', {}),
    #                             **server_created_metadata,
    #                         },
    #                     )
    #                     appointment['current_visit_id'] = current_visit_id

    #                 if appointment.get('fulfilled_visit_id') and is_valid_uuid(
    #                     appointment.get('fulfilled_visit_id')
    #                 ):
    #                     visit_exists = row_exists(
    #                         'visits', appointment.get('fulfilled_visit_id')
    #                     )
    #                     if not visit_exists:
    #                         fulfilled_visit_id = upsert_visit(
    #                             appointment.get('fulfilled_visit_id'),
    #                             patient_id,
    #                             clinic_id,
    #                             user_id,
    #                             appointment.get('provider_name', ''),
    #                             appointment.get('check_in_timestamp', utc.now()),
    #                             {
    #                                 **appointment.get('metadata', {}),
    #                                 **server_created_metadata,
    #                             },
    #                         )
    #                         appointment['fulfilled_visit_id'] = fulfilled_visit_id
    #                 else:
    #                     # If there is no valid fulfilled_visit_id uuid, force it to be null
    #                     appointment['fulfilled_visit_id'] = None

    #                 # AT THIS POINT: The visits are verified to exist. we can safely use them.
    #                 # AT THIS POINT: We assume the patient, providers and clinic exit. if not, crashing is the right action.
    #                 cur.execute(
    #                     """
    #                     INSERT INTO appointments
    #                         (id, timestamp, duration, reason, notes, provider_id, clinic_id, patient_id, user_id, status, current_visit_id, fulfilled_visit_id, metadata, created_at, updated_at, last_modified, is_deleted, server_created_at)
    #                     VALUES
    #                         (%(id)s, %(timestamp)s, %(duration)s, %(reason)s, %(notes)s, %(provider_id)s, %(clinic_id)s, %(patient_id)s, %(user_id)s, %(status)s, %(current_visit_id)s, %(fulfilled_visit_id)s, %(metadata)s, %(created_at)s, %(updated_at)s, %(last_modified)s, %(is_deleted)s, %(server_created_at)s)
    #                     ON CONFLICT (id) DO UPDATE
    #                     SET
    #                         timestamp=EXCLUDED.timestamp,
    #                         duration=EXCLUDED.duration,
    #                         reason=EXCLUDED.reason,
    #                         notes=EXCLUDED.notes,
    #                         provider_id=EXCLUDED.provider_id,
    #                         clinic_id=EXCLUDED.clinic_id,
    #                         patient_id=EXCLUDED.patient_id,
    #                         user_id=EXCLUDED.user_id,
    #                         status=EXCLUDED.status,
    #                         current_visit_id=EXCLUDED.current_visit_id,
    #                         fulfilled_visit_id=EXCLUDED.fulfilled_visit_id,
    #                         metadata=EXCLUDED.metadata,
    #                         created_at=EXCLUDED.created_at,
    #                         updated_at=EXCLUDED.updated_at,
    #                         last_modified=EXCLUDED.last_modified,
    #                         is_deleted=EXCLUDED.is_deleted
    #                     """,
    #                     appointment,
    #                 )

    #             for id in deltadata.deleted:
    #                 # Not making 'cancelled' appointments 'deleted' on purpose. we need to sync them
    #                 # Update the appointment to mark it as deleted
    #                 cur.execute(
    #                     """
    #                     UPDATE appointments
    #                     SET is_deleted = true, deleted_at = COALESCE(%s, CURRENT_TIMESTAMP)
    #                     WHERE id = %s
    #                     """,
    #                     (last_pushed_at, id),
    #                 )
    #             # for id in deltadata.deleted:
    #             #     # Not making 'cancelled' appointments 'deleted' on purpose. we need to sync them
    #             #     cur.execute(
    #             #         """UPDATE appointments SET is_deleted=true, deleted_at=%s WHERE id=%s;""",
    #             #         (last_pushed_at, id)
    #             #     )
    #             conn.commit()
    #         except Exception as e:
    #             print(f'Appointment Errors: {str(e)}')
    #             logging.error(f'Appointment Errors: {str(e)}')
    #             conn.rollback()
    #             raise e

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
                query += ' AND a.status = %(status)s'
                params['status'] = filters['status']

            if 'patient_id' in filters:
                query += ' AND a.patient_id = %(patient_id)s'
                params['patient_id'] = filters['patient_id']

            if 'provider_id' in filters:
                query += ' AND a.provider_id = %(provider_id)s'
                params['provider_id'] = filters['provider_id']

            if 'clinic_id' in filters:
                query += ' AND a.clinic_id = %(clinic_id)s'
                params['clinic_id'] = filters['clinic_id']

            cur.execute(query, params)
            return cur.fetchall()


@core.dataentity
class Prescription(SyncToClient, SyncToServer, SimpleCRUD):
    TABLE_NAME = 'prescriptions'

    id: str
    patient_id: str
    provider_id: str
    filled_by: str | None = None
    pickup_clinic_id: str
    visit_id: str | None = None
    priority: str = 'normal'
    expiration_date: fields.UTCDateTime | None = None
    prescribed_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    filled_at: fields.UTCDateTime | None = None
    status: str = 'pending'
    items: list = dataclasses.field(default_factory=list)
    notes: str = ''
    metadata: dict = dataclasses.field(default_factory=dict)
    created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    updated_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    deleted_at: fields.UTCDateTime | None = None
    last_modified: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)
    server_created_at: fields.UTCDateTime = fields.UTCDateTime(default_factory=utc.now)

    @classmethod
    def transform_delta(cls, ctx, action, data):
        if action == sync.ACTION_CREATE or action == sync.ACTION_UPDATE:
            prescription = dict(data)
            prescription.update(
                prescribed_at=get_from_dict(
                    data, 'prescribed_at', utc.from_unixtimestamp, utc.now()
                ),
                filled_by=data.get('filled_by', None),
                notes=data.get('notes', ''),
                status=data.get('status', 'pending'),
                priority=data.get('priority', None),
                expiration_date=get_from_dict(
                    data, 'expiration_date', utc.from_unixtimestamp
                ),
                visit_id=data.get('visit_id'),
                filled_at=get_from_dict(data, 'filled_at', utc.from_unixtimestamp),
                created_at=get_from_dict(
                    data, 'created_at', utc.from_unixtimestamp, utc.now()
                ),
                updated_at=get_from_dict(
                    data, 'updated_at', utc.from_unixtimestamp, utc.now()
                ),
                deleted_at=get_from_dict(data, 'deleted_at', utc.from_unixtimestamp),
                last_modified=get_from_dict(
                    data, 'last_modified', utc.from_unixtimestamp, utc.now()
                ),
                is_deleted=data.get('is_deleted', False),
                items=safe_json_dumps(data.get('items')),
                metadata=safe_json_dumps(data.get('metadata')),
            )

            if action == sync.ACTION_CREATE:
                prescription.update(
                    server_created_at=get_from_dict(
                        data, 'server_created_at', utc.from_unixtimestamp, utc.now()
                    ),
                )

            return prescription

    @classmethod
    def create_from_delta(cls, ctx, cur: Cursor, data: dict):
        print('PEEK ON CREATE:', data)

        cur.execute(
            """
            INSERT INTO prescriptions
                (id, patient_id, provider_id, filled_by, pickup_clinic_id, visit_id, priority, expiration_date, prescribed_at, filled_at, status, items, notes, metadata, is_deleted, created_at, updated_at, deleted_at, last_modified, server_created_at)
            VALUES
                (%(id)s, %(patient_id)s, %(provider_id)s, %(filled_by)s, %(pickup_clinic_id)s, %(visit_id)s, %(priority)s, %(expiration_date)s, %(prescribed_at)s, %(filled_at)s, %(status)s, %(items)s, %(notes)s, %(metadata)s, %(is_deleted)s, %(created_at)s, %(updated_at)s, %(deleted_at)s, %(last_modified)s, %(server_created_at)s)
            ON CONFLICT (id) DO UPDATE
            SET
                patient_id=EXCLUDED.patient_id,
                provider_id=EXCLUDED.provider_id,
                filled_by=EXCLUDED.filled_by,
                pickup_clinic_id=EXCLUDED.pickup_clinic_id,
                visit_id=EXCLUDED.visit_id,
                priority=EXCLUDED.priority,
                expiration_date=EXCLUDED.expiration_date,
                prescribed_at=EXCLUDED.prescribed_at,
                filled_at=EXCLUDED.filled_at,
                status=EXCLUDED.status,
                items=EXCLUDED.items,
                notes=EXCLUDED.notes,
                metadata=EXCLUDED.metadata,
                is_deleted=EXCLUDED.is_deleted,
                created_at=EXCLUDED.created_at,
                updated_at=EXCLUDED.updated_at,
                deleted_at=EXCLUDED.deleted_at,
                last_modified=EXCLUDED.last_modified
            """,
            data,
        )

    @classmethod
    def update_from_delta(cls, ctx, cur: Cursor, data: dict):
        return cls.create_from_delta(ctx, cur, data)

    @classmethod
    def delete_from_delta(cls, ctx, cur: Cursor, id: str):
        cur.execute(
            """
            UPDATE prescriptions
            SET is_deleted = true, deleted_at = COALESCE(%s, CURRENT_TIMESTAMP)
            WHERE id = %s
            """,
            (ctx.last_pushed_at, id),
        )

    @classmethod
    def search(cls, filters):
        with db.get_connection().cursor(row_factory=dict_row) as cur:
            query = """
            SELECT
                p.*,
                json_build_object(
                    'given_name', pt.given_name,
                    'surname', pt.surname,
                    'date_of_birth', pt.date_of_birth,
                    'sex', pt.sex,
                    'phone', pt.phone
                ) AS patient,
                json_build_object(
                    'name', u.name
                ) AS provider,
                json_build_object(
                    'name', c.name
                ) AS pickup_clinic
            FROM prescriptions p
            LEFT JOIN patients pt ON p.patient_id = pt.id
            LEFT JOIN users u ON p.provider_id = u.id
            LEFT JOIN clinics c ON p.pickup_clinic_id = c.id
            WHERE p.is_deleted = false
            AND p.prescribed_at >= %(start_date)s
            AND p.prescribed_at <= %(end_date)s
            """
            params = {
                'start_date': filters['start_date'],
                'end_date': filters['end_date'],
            }

            if 'status' in filters and filters['status'] != 'all':
                query += ' AND p.status = %(status)s'
                params['status'] = filters['status']

            if 'patient_id' in filters:
                query += ' AND p.patient_id = %(patient_id)s'
                params['patient_id'] = filters['patient_id']

            if 'provider_id' in filters:
                query += ' AND p.provider_id = %(provider_id)s'
                params['provider_id'] = filters['provider_id']

            if 'pickup_clinic_id' in filters:
                query += ' AND p.pickup_clinic_id = %(pickup_clinic_id)s'
                params['pickup_clinic_id'] = filters['pickup_clinic_id']

            cur.execute(query, params)
            return cur.fetchall()


######### HELPER DB METHODS #########


# Upsert a patient visit into the table
def upsert_visit(
    visit_id: str | None,
    patient_id: str,
    clinic_id: str | None,
    provider_id: str | None,
    provider_name: str | None,
    check_in_timestamp: datetime,
    metadata: dict | None = None,
    is_deleted: bool = False,
):
    """
    Upsert a visit into the table.
    This makes sure a visit exists and handles conflicts of primary keys (visit_id)
    """
    vid = visit_id
    if vid is None:
        vid = str(uuid.uuid4())

    current_time = utc.now()

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO visits (
                    id, patient_id, clinic_id, provider_id, provider_name,
                    check_in_timestamp, is_deleted, metadata,
                    created_at, updated_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    patient_id = EXCLUDED.patient_id,
                    clinic_id = EXCLUDED.clinic_id,
                    provider_id = EXCLUDED.provider_id,
                    provider_name = EXCLUDED.provider_name,
                    check_in_timestamp = EXCLUDED.check_in_timestamp,
                    is_deleted = EXCLUDED.is_deleted,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at,
                    last_modified = EXCLUDED.last_modified
                RETURNING id;
                """,
                (
                    vid,
                    patient_id,
                    clinic_id,
                    provider_id,
                    provider_name,
                    check_in_timestamp,
                    is_deleted,
                    safe_json_dumps(metadata or {}),
                    current_time,
                    current_time,
                    current_time,
                ),
            )

            result = cur.fetchone()
            conn.commit()
            return vid  # Return the visit_id


def insert_placeholder_patient(conn, patient_id, is_deleted=False):
    # Fixed timestamp for June 1, 2010
    fixed_timestamp = datetime(2010, 6, 1, 0, 0, 0)

    with conn.cursor() as cur:
        try:
            placeholder_data = {
                'id': patient_id,
                'given_name': 'Placeholder',
                'surname': 'Patient',
                'date_of_birth': date.today(),
                'sex': 'Unknown',
                'camp': '',
                'citizenship': '',
                'hometown': '',
                'phone': '',
                'additional_data': json.dumps({}),
                'government_id': None,
                'external_patient_id': None,
                'created_at': fixed_timestamp,
                'updated_at': fixed_timestamp,
                'last_modified': fixed_timestamp,
                'server_created_at': fixed_timestamp,
                'deleted_at': fixed_timestamp if is_deleted else None,
                'is_deleted': is_deleted,
                'image_timestamp': None,
                'photo_url': '',
            }

            cur.execute(
                """
                INSERT INTO patients (
                    id, given_name, surname, date_of_birth, sex, camp, citizenship, hometown, phone,
                    additional_data, government_id, external_patient_id, created_at, updated_at,
                    last_modified, server_created_at, deleted_at, is_deleted, image_timestamp, photo_url
                ) VALUES (
                    %(id)s, %(given_name)s, %(surname)s, %(date_of_birth)s, %(sex)s, %(camp)s,
                    %(citizenship)s, %(hometown)s, %(phone)s, %(additional_data)s, %(government_id)s,
                    %(external_patient_id)s, %(created_at)s, %(updated_at)s, %(last_modified)s,
                    %(server_created_at)s, %(deleted_at)s, %(is_deleted)s, %(image_timestamp)s, %(photo_url)s
                )
            """,
                placeholder_data,
            )

            conn.commit()
            print(f'Placeholder patient with ID {patient_id} inserted successfully.')
        except Exception as e:
            conn.rollback()
            print(f'Error inserting placeholder patient: {str(e)}')


# Check if a row exists in a table given its id
def row_exists(table_name: str, id: str) -> bool:
    """
    Check if a row exists in a table given its id.

    Args:
    table_name (str): The name of the table to check.
    id (str): The id of the row to check for.

    Returns:
    bool: True if the row exists, False otherwise.
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT EXISTS(
                    SELECT 1 FROM {table_name}
                    WHERE id = %s
                )
                """,
                (id,),
            )

            val = cur.fetchone()
            if val is None:
                return False

            return val[0]
