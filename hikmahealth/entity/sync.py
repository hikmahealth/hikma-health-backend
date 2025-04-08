from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, override

from psycopg import Cursor
from psycopg.connection import Connection
from psycopg.rows import dict_row

from hikmahealth import sync
from hikmahealth.entity import core
from hikmahealth.sync.errors import SyncPushError
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


@dataclass
class SyncContext:
    last_pushed_at: datetime.datetime


class SyncToServer(ISyncPush[Connection]):
    """Abstract for entities that expect to apply changes from client to server"""

    @classmethod
    @abstractmethod
    def transform_delta(cls, ctx: SyncContext, action: str, data: Any) -> dict | str:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def create_from_delta(cls, ctx: SyncContext, cur: Cursor, data: dict):
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def update_from_delta(cls, ctx: SyncContext, cur: Cursor, data: dict):
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def delete_from_delta(cls, ctx: SyncContext, cur: Cursor, id: str):
        raise NotImplementedError()

    @classmethod
    def apply_delta_changes(
        cls,
        deltadata: sync.DeltaData[dict, dict, str],
        last_pushed_at: datetime.datetime,
        conn: Connection,
    ):
        ctx = SyncContext(last_pushed_at)

        with conn.cursor() as cur:
            try:
                # `cur.executemany` can be used instead
                # batched updates??
                for action, data in deltadata:
                    transformed_data = data

                    try:
                        transformed_data = cls.transform_delta(ctx, action, data)
                    except NotImplementedError:
                        # if `transformed_data` logic missing,
                        # proceed with the same untransformed one
                        pass

                    if action in (sync.ACTION_CREATE, sync.ACTION_UPDATE):
                        assert isinstance(transformed_data, dict), 'data must be a dict'

                        if action == sync.ACTION_CREATE:
                            cls.create_from_delta(ctx, cur, transformed_data)
                        elif action == sync.ACTION_UPDATE:
                            cls.update_from_delta(ctx, cur, transformed_data)

                    elif action == sync.ACTION_DELETE:
                        assert isinstance(transformed_data, str), (
                            'transformed data must be a string'
                        )

                        cls.delete_from_delta(ctx, cur, transformed_data)

                # should commit the entire delta, or not
                conn.commit()
            except Exception as e:
                print(f'{cls.__name__} sync errors: {str(e)}')
                conn.rollback()
                raise SyncPushError(*e.args)
