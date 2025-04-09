"""Testing suite for visits"""

import datetime
import uuid

from psycopg import Connection

from hikmahealth.entity import hh
import pytest

from hikmahealth.entity.sync import SyncContext

# from hikmahealth.server.client.db import get_connection
from hikmahealth.sync.data import DeltaData
from hikmahealth.utils.misc import safe_json_dumps


@pytest.fixture()
def visit_data(db: Connection, clinic_data, patient_data, provider_data):
    yield dict(
        clinic_id=clinic_data.id,
        patient_id=patient_data.id,
        provider_id=provider_data['id'],
        provider_name=provider_data['name'],
        metadata=safe_json_dumps(dict()),
        check_in_timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
    )


@pytest.fixture(scope='class')
def visit_uuid(db):
    id = uuid.uuid1()
    yield id

    with db.cursor() as cur:
        cur.execute('DELETE FROM visits WHERE id = %s', [id])


class TestVisitSync:
    def test_creating_visit_object(self, visit_data):
        # inits a visit object
        rest = visit_data
        hh.Visit(id=str(uuid.uuid1()), **rest)

    @pytest.fixture(autouse=True)
    def sync_context(self, db):
        yield SyncContext(datetime.datetime.now(tz=datetime.UTC), conn=db)

    # @pytest.mark.order(1)
    def test_apply_create_action(self, db, visit_uuid, visit_data, sync_context):
        ctx = sync_context
        rest = visit_data | dict(id=str(visit_uuid))

        # visit_record should contain all the information it needs to be synced up
        visit_record = hh.Visit.transform_delta(ctx, 'UPDATE', rest)
        assert isinstance(visit_record, dict), 'data is not dict'

        with db.cursor() as cur:
            hh.Visit.create_from_delta(
                ctx,
                cur,
                visit_record,
            )

        db.commit()

    # @pytest.mark.order(2)
    def test_apply_update_action(self, db, visit_uuid, sync_context):
        visit = hh.Visit.from_id(str(visit_uuid))
        assert visit is not None, 'visit record with id={} must exist'.format(
            str(visit_uuid)
        )

        updated_record = hh.Visit.transform_delta(
            sync_context,
            'CREATE',
            visit.to_dict() | dict(metadata=safe_json_dumps({'test': 'completed'})),
        )
        assert isinstance(updated_record, dict), 'data is not dict'

        assert updated_record != visit.to_dict(), (
            'The update record is the SAME as the original'
        )

        with db.cursor() as cur:
            hh.Visit.update_from_delta(
                sync_context,
                cur,
                updated_record,
            )

        db.commit()

    # @pytest.mark.order(3)
    def test_apply_delete_action(self, db, visit_uuid, sync_context):
        visit = hh.Visit.from_id(str(visit_uuid))
        assert visit is not None, 'visit record with id={} must exist'.format(
            str(visit_uuid)
        )

        with db.cursor() as cur:
            hh.Visit.delete_from_delta(
                sync_context,
                cur,
                visit.id,
            )

        db.commit()
