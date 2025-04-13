import datetime
import os
from typing import Generator
import uuid
import pytest
from flask import Flask
from hikmahealth.entity import hh
from hikmahealth.server.server import app as create_app
import psycopg
from dotenv import load_dotenv

from hikmahealth.sync.data import DeltaData
from tests.entity.visits_test import SyncContext

load_dotenv('../../app/.env', verbose=True, override=True)
load_dotenv('../../.env', verbose=True, override=True)


test_email = os.getenv('TEST_EMAIL')
test_password = os.getenv('TEST_PASSWORD')


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app
    app.config.update({
        'TESTING': True,
    })
    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """Provide authentication headers for test requests"""
    import base64

    # Create basic auth header
    credentials = f'{test_email}:{test_password}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    return {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json',
    }


@pytest.fixture(scope='session')
def test_db():
    """
    Connect to the remote test database specified in .env
    This fixture has session scope, so the connection persists for the entire test session.
    """
    database_url = os.getenv('DATABASE_URL')
    print(
        'Connecting to database:', database_url.split('@')[1].split('/')[0]
    )  # Only print host/db info, not credentials

    if not database_url:
        pytest.skip('DATABASE_URL not set in .env file')

    try:
        # Connect to the remote database
        conn = psycopg.connect(database_url)
        yield conn
        conn.close()
    except psycopg.OperationalError as e:
        pytest.skip(f'Could not connect to remote database: {str(e)}')
    except Exception as e:
        pytest.skip(f'Unexpected error connecting to database: {str(e)}')


@pytest.fixture(scope='session')
def db():
    """
    Connect to the remote test database specified in .env
    This fixture has session scope, so the connection persists for the entire test session.
    """
    database_url = os.environ.get('DATABASE_URL', None)
    assert database_url is not None, 'missing DATABASE_URL from environment variables'

    print(
        'Connecting to database:', database_url.split('@')[1].split('/')[0]
    )  # Only print host/db info, not credentials

    if not database_url:
        pytest.skip('DATABASE_URL not set in .env file')

    try:
        # Connect to the remote database
        conn = psycopg.connect(database_url)
        yield conn
        conn.close()
    except psycopg.OperationalError as e:
        pytest.skip(f'Could not connect to remote database: {str(e)}')
    except Exception as e:
        pytest.skip(f'Unexpected error connecting to database: {str(e)}')


@pytest.fixture(scope='module')
def clinic_data(db: psycopg.Connection):
    clinic = hh.Clinic(
        id=str(uuid.uuid1()), name='Test Clinic', attributes=['laboratory']
    )

    with db.cursor() as cur:
        # this is the temporary implementation
        cur.execute(
            """
            INSERT INTO clinics (id, name, created_at, updated_at)
            VALUES (%(id)s, %(name)s, %(created_at)s, %(updated_at)s)
            """,
            clinic.to_dict(),
        )

    yield clinic

    with db.cursor() as cur:
        cur.execute('DELETE FROM clinics WHERE id = %s', [clinic.id])


@pytest.fixture(scope='module')
def visit_data(db: psycopg.Connection, clinic_data, patient_data, provider_data):
    last_pushed_at = datetime.datetime.now(tz=datetime.UTC)
    ctx = SyncContext(last_pushed_at, conn=db)
    visit = hh.Visit.transform_delta(
        ctx,
        'CREATE',
        dict(
            id=str(uuid.uuid1()),
            clinic_id=clinic_data.id,
            patient_id=patient_data.id,
            check_in_timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
            provider_id=provider_data['id'],
            provider_name=provider_data['name'],
            metadata=dict(),
        ),
    )

    assert visit is not None, 'visit is None'

    with db.cursor() as cur:
        hh.Visit.create_from_delta(ctx, cur, visit)

    yield visit

    with db.cursor() as cur:
        cur.execute('DELETE FROM visits WHERE id = %s', [visit['id']])


@pytest.fixture(scope='module')
def patient_data(db: psycopg.Connection):
    patient = hh.Patient(id=str(uuid.uuid1()))

    now = datetime.datetime.now(tz=datetime.UTC)
    _2daysago = now - datetime.timedelta(days=2)

    hh.Patient.apply_delta_changes(
        DeltaData(created=[patient.to_dict()]), _2daysago, db
    )

    yield patient

    with db.cursor() as cur:
        cur.execute('DELETE FROM patients WHERE id = %s', [patient.id])


@pytest.fixture(scope='module')
def provider_data(db: psycopg.Connection, clinic_data):
    provider = dict(
        id=str(uuid.uuid1()),
        name='Fake Provider',
        role='superadmin',
        email=f'test-{uuid.uuid4()}@test.com',
        hashed_password=b'bcrypt_hashed_password',
        clinic_id=clinic_data.id,
    )

    with db.cursor() as cur:
        # should have a few users that exist in the life time of the entire test suit
        cur.execute(
            """
            INSERT INTO users (id, name, role, email, hashed_password, clinic_id)
            VALUES
            (%(id)s, %(name)s, %(role)s, %(email)s, %(hashed_password)s, %(clinic_id)s)""",
            provider,
        )

    yield provider

    with db.cursor() as cur:
        cur.execute('DELETE FROM patients WHERE id = %s', [provider['id']])
