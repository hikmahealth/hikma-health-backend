from __future__ import annotations

from typing import override

from psycopg.connection import Connection
from psycopg.rows import dict_row

from hikmahealth.entity import core
from hikmahealth.sync.operation import ISyncPull, ISyncPush
from hikmahealth.utils.datetime import local as dtutils

import datetime
from hikmahealth.sync import DeltaData


# should be move to a different structure. since it depends on psycopg to
# execute properly
class SyncToClient(ISyncPull[Connection], core.Entity):
    """For entity that expects to apply changes from server to client"""

    @classmethod
    @override
    def get_delta_records(cls, last_sync_time: datetime.datetime, conn: Connection):
        # print(last_sync_time)
        with conn.cursor(row_factory=dict_row) as cur:
            newrecords = cur.execute(
                'SELECT * from {} WHERE server_created_at > %s AND deleted_at IS NULL AND is_deleted = false'.format(
                    cls.TABLE_NAME
                ),
                (last_sync_time,),
            ).fetchall()

            updatedrecords = cur.execute(
                'SELECT * FROM {} WHERE last_modified > %s AND server_created_at < %s AND deleted_at IS NULL AND is_deleted = false'.format(
                    cls.TABLE_NAME
                ),
                (last_sync_time, last_sync_time),
            ).fetchall()

            deleterecords = cur.execute(
                'SELECT id FROM {} WHERE deleted_at > %s AND is_deleted = true'.format(
                    cls.TABLE_NAME
                ),
                (last_sync_time,),
            ).fetchall()

        return DeltaData(
            created=newrecords,
            updated=updatedrecords,
            deleted=[row['id'] for row in deleterecords],
        )


class SyncToServer(ISyncPush[Connection]):
    """Abstract for entities that expect to apply changes from client to server"""

    pass
