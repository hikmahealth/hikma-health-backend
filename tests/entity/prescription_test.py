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
def prescription_data(db: Connection, clinic_data, patient_data, provider_data):
    yield dict(
        pickup_clinic_id=clinic_data.id,
        patient_id=patient_data.id,
        provider_id=provider_data['id'],
        metadata=safe_json_dumps(dict()),
        check_in_timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
    )


@pytest.fixture(scope='class')
def prescription_uuid(db):
    id = uuid.uuid1()
    yield id

    with db.cursor() as cur:
        cur.execute('DELETE FROM prescriptions WHERE id = %s', [id])


@pytest.fixture(autouse=True)
def sync_context(db):
    yield SyncContext(datetime.datetime.now(tz=datetime.UTC), conn=db)


class TestPrescriptonSync:
    def test_creating_prescription_object(self, prescription_data):
        hh.Prescription(id=str(uuid.uuid1()), **prescription_data)

    # @pytest.mark.order(1)
    def test_apply_create_action(
        self, db, prescription_uuid, prescription_data, sync_context
    ):
        ctx = sync_context
        rest = prescription_data | dict(id=str(prescription_uuid))

        # visit_record should contain all the information it needs to be synced up
        record = hh.Prescription.transform_delta(ctx, 'CREATE', rest)
        print('CREATE', record)
        assert isinstance(record, dict), 'data is not dict'

        with db.cursor() as cur:
            hh.Prescription.create_from_delta(
                ctx,
                cur,
                record,
            )

        db.commit()

    # @pytest.mark.order(2)
    def test_apply_update_action(self, db, prescription_uuid, sync_context):
        d = hh.Prescription.from_id(str(prescription_uuid))
        assert d is not None, 'prescription record with id={} must exist'.format(
            str(prescription_uuid)
        )

        updated_record = hh.Prescription.transform_delta(
            sync_context,
            'UPDATE',
            d.to_dict()
            | dict(status='completed', metadata=safe_json_dumps({'test': 'completed'})),
        )
        assert isinstance(updated_record, dict), 'data is not dict'

        assert updated_record != d.to_dict(), (
            'The update record is the SAME as the original'
        )

        with db.cursor() as cur:
            hh.Prescription.update_from_delta(
                sync_context,
                cur,
                updated_record,
            )

        db.commit()

    # @pytest.mark.order(3)
    def test_apply_delete_action(self, db, prescription_uuid, sync_context):
        visit = hh.Prescription.from_id(str(prescription_uuid))
        assert visit is not None, 'prescription record with id={} must exist'.format(
            str(prescription_uuid)
        )

        with db.cursor() as cur:
            hh.Prescription.delete_from_delta(
                sync_context,
                cur,
                visit.id,
            )

        db.commit()
