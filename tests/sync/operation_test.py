import datetime
from hikmahealth.sync.data import DeltaData
from hikmahealth.sync.errors import SyncPushError
from hikmahealth.sync.operation import Sink

import pytest


def test_sync_operations():
    sinkdata = Sink()

    now = datetime.datetime.now()
    dx = DeltaData(created=[1, 2])

    class TriggerClass:
        @classmethod
        def apply_delta_changes(cls, deltadata, lastat, val):
            nonlocal dx
            assert val == 1
            assert now == lastat

            dx = dx.add(
                created=deltadata.created,
                updated=deltadata.updated,
                deleted=deltadata.deleted,
            )

    sinkdata.add('triggerclass', TriggerClass)
    sinkdata.push('triggerclass', DeltaData(created=[10, 20]), now, 1)

    def do_trigger(deltadata, lastat, val):
        nonlocal dx
        assert val == 1
        assert now == lastat

        dx = dx.add(
            created=deltadata.created,
            updated=deltadata.updated,
            deleted=deltadata.deleted,
        )

    sinkdata.add('trigger', do_trigger)
    sinkdata.push('trigger', DeltaData(created=[3, 4]), now, 1)

    sinkdata.push('KEYNOTEXISTS', DeltaData(), now, 1213123)  # should be ignored
    sinkdata.remove('trigger')
    sinkdata.push('trigger', DeltaData(created=[5, 6]), now, 2)  # this shouldn't work

    assert set(dx) == set([
        ('CREATE', 1),
        ('CREATE', 2),
        ('CREATE', 3),
        ('CREATE', 4),
        ('CREATE', 10),
        ('CREATE', 20),
    ])

    def do_raise_error(*args):
        raise Exception('failed')

    sinkdata.add('value', do_raise_error)

    with pytest.raises(SyncPushError):
        sinkdata.push('value', DeltaData(), now, 13232)
