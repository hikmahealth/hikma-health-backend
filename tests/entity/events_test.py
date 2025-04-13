"""Testing suite for visits"""

import datetime
import uuid

from boto3.utils import sys
from psycopg import Connection

from hikmahealth.entity import hh
import pytest

from hikmahealth.entity.sync import SyncContext

from hikmahealth.utils.misc import safe_json_dumps
from tests.entity.visits_test import DeltaData


@pytest.fixture()
def complete_event_data(db: Connection, event_uuid, patient_data, visit_data):
    yield dict(
        id=event_uuid,
        patient_id=patient_data.id,
        visit_id=visit_data['id'],
        check_in_timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
    )


@pytest.fixture()
def partial_event_data(db: Connection, event_uuid):
    """Information generated here are used in forcing upsert of patient, forms and visit that may not exists"""
    new_patient_not_exist_uuid = uuid.uuid1()
    new_visit_not_exist_uuid = uuid.uuid1()

    yield dict(
        id=event_uuid,
        patient_id=str(new_patient_not_exist_uuid),
        visit_id=str(new_visit_not_exist_uuid),
        created_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
        updated_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
    )


@pytest.fixture(scope='class')
def event_uuid(db):
    id = uuid.uuid1()
    yield str(id)

    with db.cursor() as cur:
        cur.execute('DELETE FROM events WHERE id = %s', [id])


@pytest.fixture()
def last_pushed_at():
    return datetime.datetime.now(tz=datetime.UTC)


@pytest.fixture(autouse=True)
def sync_context(db, last_pushed_at):
    yield SyncContext(last_pushed_at, conn=db)


class TestProperEventsSync:
    def test_create_object(self, complete_event_data):
        hh.Event(**complete_event_data)

    def test_create_object_from_partial(self, partial_event_data):
        hh.Event(**partial_event_data)

    def test_returned_norma_data_after_create(self, sync_context, complete_event_data):
        out = hh.Event.transform_delta(sync_context, 'CREATE', complete_event_data)
        print('EVENT SHAPE', out)

    def test_syncing_logic_with_complete_data(
        self, event_uuid, db, complete_event_data, last_pushed_at
    ):
        ddata = DeltaData().add(created=[complete_event_data])
        hh.Event.apply_delta_changes(ddata, last_pushed_at, db)

    def test_syncing_logic_with_partial_data(
        self, db, partial_event_data, last_pushed_at
    ):
        ddata = DeltaData().add(created=[partial_event_data])
        hh.Event.apply_delta_changes(ddata, last_pushed_at, db)
