from __future__ import annotations

from abc import abstractmethod
from typing import override

from psycopg.connection import Connection
from psycopg.rows import dict_row

from hikmahealth.entity import core
from hikmahealth.utils.datetime import local as dtutils

import datetime

class ISyncDown(object):
    @classmethod
    @abstractmethod
    def get_delta_records(self, last_sync_time: int | str, *args, **kwargs) -> DeltaData:
        """Return the difference in data that was created, updated, or deleted since
         last sync time.
         
         Implement this to prevent the code base from exploding"""
        raise NotImplementedError()

class DeltaData(object):
    """Handles database delta data"""
    def __init__(self, 
                 created: list[dict] | None = None, 
                 updated: list[dict] | None = None, 
                 deleted: list[str] | None = None):
        self.created = created if created is not None else []
        self.updated = updated if updated is not None else []
        self.deleted = deleted if deleted is not None else []

    def to_dict(self):
        return dict(
            created=self.created,
            updated=self.updated,
            deleted=self.deleted
        )
    
    @property
    def is_empty(self):
        return len(self.created) == 0 and \
                len(self.deleted) == 0 and \
                len(self.updated) == 0

# should be move to a different structure. since it depends on psycopg to
# execute properly
class SyncToClientEntity(ISyncDown, core.Entity):
    """For entity that expects to apply changes from server to client

        Args:
       Example:
    """
    @classmethod
    @override
    def get_delta_records(cls, last_sync_time: datetime.datetime, conn: Connection): 
        # print(last_sync_time)
        with conn.cursor(row_factory=dict_row) as cur:
            newrecords = cur.execute(
                "SELECT * from {} WHERE server_created_at > %s AND deleted_at IS NULL"\
                    .format(cls.TABLE_NAME),
                (last_sync_time, )
            ).fetchall()

            updatedrecords = cur.execute(
            "SELECT * FROM {} WHERE last_modified > %s AND server_created_at < %s AND deleted_at IS NULL"\
                .format(cls.TABLE_NAME),
                (last_sync_time, last_sync_time),
            ).fetchall()

            deleterecords = cur.execute(
            "SELECT id FROM {} WHERE deleted_at > %s"\
                .format(cls.TABLE_NAME),
            (last_sync_time, )).fetchall()

        return DeltaData(
            created=newrecords,
            updated=updatedrecords,
            deleted=[row["id"] for row in deleterecords]
        )
        
class ISyncToServer(object):
    """Abstract for entities that expect to apply changes from client to server"""
    @classmethod
    @abstractmethod
    def apply_delta_changes(cls, deltadata: DeltaData, last_pushed_at: datetime.datetime, conn: Connection):
        raise NotImplementedError(f"require that the {__class__} implement this to syncronize from client")
    
class SyncableEntity(SyncToClientEntity, ISyncToServer):
    pass