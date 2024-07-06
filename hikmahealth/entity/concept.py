from __future__ import annotations

from hikmahealth.entity import sync

from datetime import datetime
from hikmahealth.utils import datetime as dtutils

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

            

class Patient(sync.Entity):
    TABLE_NAME = "patients"

    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        """Applies the delta changes pushed by the client to this server database.
        
        NOTE: might want to have `DeltaData` as only input and add `last_pushed_at` to deleted"""
        with conn.cursor() as cur:
            # `cur.executemany` can be used instead
            for row in deltadata.created:
                event = dict(row)
                print(event)

                event.update(
                    # TODO: should check the effects of this
                    # the date time return init posix for now.
                    # created_at=dtutils.convert_timestamp_to_iso(event["created_at"]),
                    # updated_at=dtutils.convert_timestamp_to_iso(event["updated_at"]),
                    # image_timestamp=dtutils.convert_timestamp_to_iso(event["image_timestamp"]),
                    created_at=event["created_at"],
                    updated_at=event["updated_at"],
                    image_timestamp=event["image_timestamp"],
                    additional_data=json.dumps(event["additional_data"])
                )

                # print(event)

                cur.execute(
                    """
                    INSERT INTO patients
                    (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified)
                    VALUES
                    (%(id)s, %(given_name)s, %(surname)s, %(date_of_birth)s, %(citizenship)s, %(hometown)s, %(sex)s, %(phone)s, %(camp)s, %(additional_data)s, now(), '', %(government_id)s, %(external_patient_id)s, %(created_at)s, %(updated_at)s, current_timestamp)
                    """,
                    event
                )

            # performs upserts
            for row in deltadata.updated:
                # NOTE: might want to fix this logic when dealing with aprtials
                event = dict(row)
                event.update(
                    created_at=dtutils.from_timestamp(event["created_at"]),
                    updated_at=dtutils.from_timestamp(event["updated_at"]),
                    last_modified=datetime.now()
                )
                
                # TODO: might want to find a way to safely construct the sql body safely
                cur.execute(
                    """INSERT INTO patients
                          (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, image_timestamp, photo_url, government_id, external_patient_id, created_at, updated_at, last_modified)
                        VALUES 
                          (%(id)s, %(given_name)s, %(surname)s, %(date_of_birth)s, %(citizenship)s, %(hometown)s, %(sex)s, %(phone)s, %(camp)s, %(additional_data)s, '', '', %(government_id)s, %(external_patient_id)s, %(created_at)s, %(updated_at)s, %(last_modified)s)
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
                    event
                )

            for id in deltadata.deleted:
                cur.execute(
                    """UPDATE patients SET is_deleted=true, deleted_at='%s' WHERE id = '%s';""",
                        (dtutils.from_timestamp(last_pushed_at), id)
                )


class Event(sync.Entity):
    TABLE_NAME = "events"
    
    @classmethod
    def apply_delta_changes(cls, deltadata, last_pushed_at, conn):
        with conn.cursor() as cur:
            # `cur.executemany` can be used instead
            for row in deltadata.created:
                cur.execute(
                    """"
                    INSERT INTO events
                    (id, patient_id, form_id, visit_id, event_type, form_data, metadata, is_deleted, created_at, updated_at)   
                    VALUES
                    (%(id)s, %(patient_id)s, %(form_id)s, %(visit_id)s, %(event_type)s, %(form_data)s, %(metadata)s, false, %(created_at)s, %(updated_at)s)   
                    """,
                    row 
                )

            # performs upserts
            for event in deltadata.updated:
                event = dict(event)
                event.update(
                    created_at=dtutils.from_timestamp(event["created_at"]),
                    updated_at=dtutils.from_timestamp(event["updated_at"]),
                    last_modified=datetime.now()
                )

                cur.execute(
                    """
                    UPDATE 
                        events SET
                        patient_id='%(patient_id)s',  
                        form_id='%(form_id)s', 
                        visit_id='%(visit_id)s', 
                        event_type='%(event_type)s', 
                        form_data='%(form_data)s', 
                        metadata='%(metadata)s', 
                        is_deleted='%(is_deleted)s', 
                        created_at='%(created_at)s', 
                        updated_at='%(updated_at)s', 
                        last_modified='%(last_modified)s' WHERE id='%(id)s';""", event)

            for row in deltadata.deleted:
                cur.execute(
                    f"""UPDATE events SET is_deleted=true, deleted_at='%s' WHERE id = '%s';""",
                        (dtutils.from_timestamp(last_pushed_at), row["id"])
                )

class Clinic(sync.SyncDownEntity):
    TABLE_NAME = "clinic"
    pass

class Visit(sync.SyncDownEntity):
    TABLE_NAME = "visits"