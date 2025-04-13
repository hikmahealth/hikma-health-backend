"""Testing suite for visits"""

import datetime
import json
import uuid

from boto3.utils import sys
from psycopg import Connection

from hikmahealth.entity import hh
import pytest

from hikmahealth.entity.sync import SyncContext

from hikmahealth.utils.misc import safe_json_dumps
from tests.entity.visits_test import DeltaData


@pytest.fixture()
def complete_data(
    db: Connection,
    appointment_uuid,
    patient_data,
    visit_data,
    clinic_data,
    provider_data,
):
    yield dict(
        id=appointment_uuid,
        patient_id=patient_data.id,
        current_visit_id=visit_data['id'],
        clinic_id=clinic_data.id,
        status='pending',
        user_id=provider_data['id'],
        provider_id=provider_data['id'],
        provider_name=provider_data['name'],
        timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
        duration=15,
    )


# @pytest.fixture()
# def partial_data(db: Connection, appointment_uuid, provider_data):
#     new_patient_not_exist_uuid = uuid.uuid1()
#     new_user_not_exist_uuid = uuid.uuid1()

#     yield dict(
#         id=appointment_uuid,
#         patient_id=str(new_patient_not_exist_uuid),
#         user_id=provider_data['id'],
#         provider_id=provider_data['id'],
#         provider_name=provider_data['name'],
#         created_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
#         updated_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
#     )


# @pytest.fixture()
# def bad_partial_data(db: Connection, appointment_uuid):
#     """Details here should make the PUSH fail"""
#     new_patient_not_exist_uuid = uuid.uuid1()
#     new_clinic_not_exist_uuid = uuid.uuid1()

#     yield dict(
#         id=appointment_uuid,
#         patient_id=str(new_patient_not_exist_uuid),
#         clinic_id=str(
#             new_clinic_not_exist_uuid
#         ),  # this doesn't exist. perhaps it shouldn't work
#         created_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
#         updated_at=datetime.datetime.now(tz=datetime.UTC).isoformat(),
#     )


@pytest.fixture(scope='class')
def appointment_uuid(db):
    id = uuid.uuid1()
    yield str(id)

    with db.cursor() as cur:
        cur.execute('DELETE FROM appointments WHERE id = %s', [id])


@pytest.fixture()
def last_pushed_at():
    return datetime.datetime.now(tz=datetime.UTC)


@pytest.fixture(autouse=True)
def sync_context(db, last_pushed_at):
    yield SyncContext(last_pushed_at, conn=db)


class TestAppointmentSync:
    def test_create_object(self, complete_data):
        hh.Appointment(**complete_data)

    # def test_create_object_from_partial(self, partial_data):
    #     hh.Appointment(**partial_data)

    def test_returned_normal_data_after_create(self, sync_context, complete_data):
        out = hh.Appointment.transform_delta(sync_context, 'CREATE', complete_data)
        print('APPOINTMENT SHAPE', out)

    def test_syncing_logic_with_complete_data(
        self, appointment_uuid, db, complete_data, last_pushed_at
    ):
        ddata = DeltaData().add(created=[complete_data])
        hh.Appointment.apply_delta_changes(ddata, last_pushed_at, db)

    # def test_syncing_logic_with_partial_data(self, db, partial_data, last_pushed_at):
    #     ddata = DeltaData().add(created=[partial_data])
    #     hh.Appointment.apply_delta_changes(ddata, last_pushed_at, db)
