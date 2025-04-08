from psycopg.rows import class_row, dict_row
from hikmahealth.utils.datetime import utc
import math

"""Test suite to check if the properties are syncing properties with
the state transitions happening as expected"""

from hikmahealth.entity import hh
from hikmahealth.server.client.db import get_connection
from uuid import UUID, uuid1

from datetime import datetime, timedelta

from hikmahealth.sync.data import DeltaData


# Utility function to prepare data to be inserted in the databse
def fake_patient(
    id: UUID | None = None,
    server_datetime: datetime | None = None,
    last_modified: datetime | None = None,
    dt_reference: datetime | None = None,
    deleted_at: datetime | None = None,
):
    default_date = dt_reference if dt_reference is not None else utc.now()
    default_server_date = (
        server_datetime if server_datetime is not None else default_date
    )

    return dict(
        id=str(uuid1() if id is None else id),
        given_name='Steven',
        is_deleted=deleted_at is not None,
        deleted_at=deleted_at,
        server_created_at=default_server_date,
        last_modified=last_modified,
        created_at=default_date,
        updated_at=default_date,
    )


STARTING_SIZE = 10
"""The number of entities the test suite should start with"""

DELETE_PERCENTAGE = 10
"""The percentage of entities to flag for deletion when
testing for the sync operation"""


class TestSyncToDatabase:
    """Might scrub this.

    Creating a test suite to see if syncing patients to the database would work"""

    def setup_method(self, method):
        self.db = get_connection()

        self.SERVER_CREATE_DATETIME = utc.now()

        # include script to create patient at the start of the tests
        # we start by creating patients to
        # to have patients we'd like to update
        self.created_patients = []
        with self.db.cursor(row_factory=dict_row) as cur:
            for p in [
                fake_patient(dt_reference=self.SERVER_CREATE_DATETIME)
                for _ in range(STARTING_SIZE)
            ]:
                cur.execute(
                    """INSERT INTO patients
                        (id, given_name, camp, citizenship, date_of_birth, external_patient_id, government_id, hometown, phone, sex, surname, is_deleted, deleted_at, created_at, updated_at, last_modified, server_created_at)
                        VALUES
                        (%(id)s, %(given_name)s, NULL, NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL, %(is_deleted)s, %(deleted_at)s, %(created_at)s, %(updated_at)s, %(last_modified)s, %(server_created_at)s)
                        RETURNING *;
                    """,
                    p,
                )

                self.db.commit()

                data = cur.fetchone()
                self.db.commit()

                if data is not None:
                    self.created_patients.append(data)

        count_created = len(self.created_patients)
        count_deleted = math.ceil(
            count_created * max(0, min(DELETE_PERCENTAGE, 100)) / 100
        )

        # shoudl move this to the operation
        self.to_update_patients = [
            d
            for d in (
                self.created_patients[: count_created - count_deleted]
                if count_deleted
                else []
            )
        ]

        self.to_delete_patient_ids = [
            d['id']
            for d in (
                self.created_patients[max(0, count_created - count_deleted) :]
                if count_deleted >= 1
                else []
            )
        ]

    def teardown_method(self, method):
        with self.db.cursor() as cur:
            for v in self.created_patients:
                cur.execute('DELETE FROM patients WHERE id = %s', (str(v['id']),))
                self.db.commit()

        self.db.close()

    def test_patient(self):
        # last sync was 30 days
        last_request_at = self.SERVER_CREATE_DATETIME - timedelta(days=30)

        # new data is 10 days older than ones in DB
        new_world_date = self.SERVER_CREATE_DATETIME + timedelta(days=10)

        count_new_created_records = 5

        updated_records = [
            hh.Patient(**(d | dict(given_name='Jerry'))).to_dict()
            for d in self.to_update_patients
        ]
        deltadata = DeltaData(
            created=[
                hh.Patient(**fake_patient(dt_reference=new_world_date)).to_dict()
                for _ in range(count_new_created_records)
            ],
            updated=updated_records,
            deleted=list(map(str, self.to_delete_patient_ids)),
        )

        # add the newly created data for clean up
        for d in deltadata.created:
            self.created_patients.append(d)

        # commit patient records to database
        hh.Patient.apply_delta_changes(deltadata, last_request_at, self.db)

        self.db.commit()

        # fetch all the records since last sync
        # NOTE: maybe at this point, test the PULL operation
        with self.db.cursor(row_factory=class_row(hh.Patient)) as cur:
            # TODO: include ID filter too
            cur.execute(
                """SELECT * FROM patients WHERE created_at >= %s AND is_deleted = false AND id = ANY(%s)""",
                (last_request_at, [str(v['id']) for v in self.created_patients]),
            )

            self.db.commit()
            patients = cur.fetchall()

            # this now includes the updated values
            assert len(patients) == len(self.created_patients) - len(
                self.to_delete_patient_ids
            ), "test failed, expected number of records after sync didn't match"

        self.db.commit()
