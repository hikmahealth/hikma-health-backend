"""Testing suite for visits"""

import datetime
import uuid

from psycopg import Connection

from hikmahealth.entity import hh
import pytest

from hikmahealth.entity.sync import SyncContext

from hikmahealth.utils.misc import safe_json_dumps


@pytest.fixture()
def complete_event_data(db: Connection, patient_data, visit_data):
    yield dict(
        patient_id=patient_data.id,
        visit_id=visit_data.id,
        metadata=safe_json_dumps(dict()),
        check_in_timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
    )


@pytest.fixture()
def partial_event_data(db: Connection):
    """Information generated here are used in forcing upsert of patient, forms and visit that may not exists"""
    new_patient_not_exist_uuid = uuid.uuid1()
    new_visit_not_exist_uuid = uuid.uuid1()

    yield dict(
        patient_id=str(new_patient_not_exist_uuid),
        visit_id=str(new_visit_not_exist_uuid),
        metadata=safe_json_dumps(dict()),
        created_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
        updated_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
    )


@pytest.fixture(scope='class')
def event_uuid(db):
    id = uuid.uuid1()
    yield id

    with db.cursor() as cur:
        cur.execute('DELETE FROM prescriptions WHERE id = %s', [id])


@pytest.fixture(autouse=True)
def sync_context(db):
    yield SyncContext(datetime.datetime.now(tz=datetime.UTC), conn=db)


class TestEventToUpsertDataSync:
    pass


class TestProperEventsSync:
    def test_create_object(self, event_data):
        hh.Event(id=str(uuid.uuid1()), **event_data)
