"""Testing suite for visits"""

import datetime
import uuid

from psycopg import Connection
from hikmahealth.entity import hh
import pytest

from hikmahealth.server.client.db import get_connection
from hikmahealth.sync.data import DeltaData
from hikmahealth.utils.misc import safe_json_dumps

# def setup_module():


@pytest.fixture()
def db():
    db = get_connection()
    yield db
    db.close()


@pytest.fixture()
def visit_data(db):
    # for visit record to exist, the other
    # for record due to FKI, also need to exist
    clinic = hh.Clinic(
        id=str(uuid.uuid1()), name='Test Clinic', attributes=['laboratory']
    )
    patient = hh.Patient(id=str(uuid.uuid1()))
    provider = dict(
        id=str(uuid.uuid1()),
        name='Fake Provider',
        role='superadmin',
        email=f'test-{uuid.uuid4()}@test.com',
        hashed_password=b'bcrypt_hashed_password',
        clinic_id=clinic.id,
    )

    # create clinic and patient
    with db.cursor() as cur:
        # this is the temporary implementation
        cur.execute(
            """
            INSERT INTO clinics (id, name, created_at, updated_at)
            VALUES (%(id)s, %(name)s, %(created_at)s, %(updated_at)s)
            """,
            clinic.to_dict(),
        )

        # should have a few users that exist in the life time of the entire test suit
        cur.execute(
            """
            INSERT INTO users (id, name, role, email, hashed_password, clinic_id)
            VALUES
            (%(id)s, %(name)s, %(role)s, %(email)s, %(hashed_password)s, %(clinic_id)s)""",
            provider,
        )

    db.commit()

    now = datetime.datetime.now(tz=datetime.UTC)
    _2daysago = now - datetime.timedelta(days=2)

    # create patient
    hh.Patient.apply_delta_changes(
        DeltaData(created=[patient.to_dict()]), _2daysago, db
    )

    db.commit()

    yield dict(
        clinic_id=clinic.id,
        patient_id=patient.id,
        provider_id=provider['id'],
        provider_name=provider['name'],
        metadata=safe_json_dumps(dict()),
    )

    # delete created records
    with db.cursor() as cur:
        cur.execute('DELETE FROM users WHERE id = %s', [provider['id']])
        cur.execute('DELETE FROM patients WHERE id = %s', [patient.id])
        cur.execute('DELETE FROM clinics WHERE id = %s', [clinic.id])

    db.commit()


def test_init_visit_object(visit_data):
    # inits a visit object
    rest = visit_data | dict(check_in_timestamp=datetime.datetime.now(tz=datetime.UTC))
    obj = hh.Visit(id=str(uuid.uuid1()), **rest)


def test_create_visit_to_db(db, visit_data):
    # inits an object and attempts to write it to DB
    id = str(uuid.uuid1())
    rest = visit_data | dict(check_in_timestamp=datetime.datetime.now(tz=datetime.UTC))
    visit = hh.Visit(id=id, **rest)

    with db.cursor() as cur:
        hh.Visit.create_from_delta(
            cur,
            # NOTE: since last_modified, server_created_at? aren't exposed by the
            # `hh.Visit` dataclass, thus not made available when using the
            # `.apply_delta_changes operation, hence the manual adding
            #
            # might need to revise this approach
            visit.to_dict()
            | dict(last_modified=datetime.datetime.now(tz=datetime.UTC)),
        )

    db.commit()
    yield id

    # remove visit after
    with db.cursor() as cur:
        cur.execute('DELETE FROM visits WHERE id = %s', [visit.id])
