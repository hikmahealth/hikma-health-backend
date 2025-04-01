"""
Section to facilitate performing the sync operation.
To contain entity that's separate and testable
"""

from abc import abstractmethod
from collections import OrderedDict
import datetime
from typing import Callable, Dict

from psycopg import Connection
from hikmahealth.entity import hh
from hikmahealth.server.client import db

from .data import DeltaData
from .errors import SyncPushError


type SyncPushFunction[TArgs] = Callable[[DeltaData, datetime.datetime, TArgs], None]
"""Function signature to facilitate data syncronization upon receiving changes / `DeltaData`"""


class ISyncPush[TArgs]:
    """Abstract class required to implement methods that facilitate syncronization operation
    when receiving new data"""

    @classmethod
    @abstractmethod
    def apply_delta_changes(
        cls, deltadata: DeltaData, last_pushed_at: datetime.datetime, args: TArgs
    ):
        raise NotImplementedError(
            f'require that the {__class__} implement this to syncronize from client'
        )


class ISyncPull[TArgs]:
    """Abstract class required to implement methods when to facilite fetching data to be
    synced upstream"""

    @classmethod
    @abstractmethod
    def get_delta_records(cls, last_sync_time: int | str, args: TArgs) -> DeltaData:
        """Return the difference in data that was created, updated, or deleted since
        last sync time.

        Implement this to prevent the code base from exploding"""
        raise NotImplementedError()


class Sink[TArgs]:
    """Manges the syncronization operation"""

    def __init__(
        self,
    ):
        # to contain a  list of toupuble
        self._ops: Dict[
            str,
            SyncPushFunction | ISyncPush[TArgs],
        ] = OrderedDict()
        pass

    def add(
        self,
        key: str,
        sync_operation,
    ):
        # to allow only one sync operation per key
        # NOTE: might change in the future
        assert key not in self._ops, f"key '{key}' already added to sink."

        if isinstance(sync_operation, type):
            # since this is a class, the operations below are to determine if
            # the `sync_operation` argument correctly implements the `ISyncPush` interface
            assert hasattr(sync_operation, 'apply_delta_changes'), (
                'object is missing the `apply_delta_changes` method'
            )

            assert callable(getattr(sync_operation, 'apply_delta_changes')), (
                'class `apply_delta_changes` is not a callable class method'
            )
        else:
            # since not a class, determines if the function correctly implements
            # the `SyncPushFunction` function
            assert callable(sync_operation), (
                'operation is neither a `class` nor a `function`'
            )

        self._ops[key] = sync_operation

    def remove(self, key: str):
        """Removes operation that's registered for syncronization stored in `key` argument"""
        if key in self._ops:
            del self._ops[key]

    def push(
        self,
        key: str,
        deltadata: DeltaData,
        last_synced_at: datetime.datetime,
        args: TArgs,
    ):
        """Pushes the delta operations to the available nodes using their keys"""
        try:
            operation = self._ops[key]

            if isinstance(operation, type):
                # calls the method if implements the SyncToEntityMethod
                operation.apply_delta_changes(deltadata, last_synced_at, args)
            else:
                assert callable(operation), 'somehow, the operation is not callable'

                operation(deltadata, last_synced_at, args)

        except KeyError:
            print(f'WARN: missing operation for key={key}')


if __name__ == '__main__':
    # operation to sync the service to server
    sink = Sink[Connection]()

    # queueing things for syncing
    # order matters
    sink.add('patients', hh.Patient)
    sink.add('patient_additional_attributes', hh.PatientAttribute)
    sink.add('visits', hh.Visit)
    sink.add('events', hh.Event)
    sink.add('appointments', hh.Appointment)
    sink.add('prescriptions', hh.Prescription)

    with db.get_connection() as conn:
        try:
            for key, newdelta in [
                (
                    'patients',
                    DeltaData(created=None, updated=None, deleted=['1231231232']),
                ),
            ]:
                sink.push(key, newdelta, datetime.datetime(), conn)
            # after leaving the context, there's an implied db.commit()
        except Exception as err:
            raise SyncPushError(f'failed to perform sync operation. reason: {err}')
