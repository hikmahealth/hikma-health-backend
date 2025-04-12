import datetime
from hikmahealth.sync.data import DeltaData
from hikmahealth.sync.operation import Sink


def test_sync_operations():
    sinkdata = Sink()

    now = datetime.datetime.now()
    dx = DeltaData(created=[1, 2])

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

    assert set(dx) == set([
        ('CREATE', 1),
        ('CREATE', 2),
        ('CREATE', 3),
        ('CREATE', 4),
    ])
