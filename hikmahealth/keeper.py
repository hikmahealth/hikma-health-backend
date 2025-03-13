"""
Utility to help manage server variables to be created by a user of backend service
"""

import base64
import json
from typing import Any
import uuid

from psycopg.rows import dict_row
from hikmahealth.server.client import db
import hashlib

VALUE_TYPE_STRING = 'string'
VALUE_TYPE_NUMBER = 'number'
VALUE_TYPE_BOOLEAN = 'boolean'
VALUE_TYPE_BLOB = 'blob'
VALUE_TYPE_JSON = 'json'

valid_types = [
    VALUE_TYPE_STRING,
    VALUE_TYPE_NUMBER,
    VALUE_TYPE_BOOLEAN,
    VALUE_TYPE_BLOB,
    VALUE_TYPE_JSON,
]


class Keeper:
    """To facilitate the management of server variables"""

    def __init__(self):
        pass

    def get_json(self, key: str):
        vtype, vdata = self.get_primitive(key)
        if vtype is None or vdata is None:
            return None

        if vtype == VALUE_TYPE_JSON:
            return json.loads(base64.b64decode(vdata))

        raise ValueError('no such value')

    def get_primitive(self, key: str):
        with db.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(
                    """
                        SELECT value_type, value_data
                        FROM server_variables
                        WHERE key = %s LIMIT 1;
                        """,
                    (key.lower(),),
                ).fetchone()

                if row is None:
                    return (None, None)

                vtype = row['value_type']
                vdata: bytes | None = row['value_data']

                if vdata is None:
                    return (vtype, None)

                return vtype, vdata

    def get(self, key: str):
        """Attempts to fetch a server variable"""
        vtype, vdata = self.get_primitive(key)
        if vtype is None or vdata is None:
            return None

        if vtype == VALUE_TYPE_BOOLEAN:
            return True if vdata == b'1' else False
        if vtype == VALUE_TYPE_STRING:
            return vdata.decode('utf-8')
        if vtype == VALUE_TYPE_NUMBER:
            return int.from_bytes(vdata)
        if vtype == VALUE_TYPE_BLOB:
            return vdata

        print(
            f"WARN: invalid type. for json data, use self.get_json() '{vtype}' not in {valid_types}"
        )
        return None

    def set_str(self, key: str, value: str):
        self.set_primitive(
            key,
            str.encode(value),
            VALUE_TYPE_STRING,
        )

    def set_boolean(self, key: str, value: bool):
        self.set_primitive(key, value.to_bytes(), VALUE_TYPE_BOOLEAN)

    def set_number(self, key: str, value: int):
        self.set_primitive(key, value.to_bytes(), VALUE_TYPE_NUMBER)

    def set_blob(self, key: str, value: bytes):
        self.set_primitive(key, value, VALUE_TYPE_BLOB)

    def set_json(self, key: str, value: Any):
        data = base64.b64encode(json.dumps(value).encode('utf-8'))
        self.set_primitive(key, data, VALUE_TYPE_JSON)

    def set_primitive(
        self, key: str, value: bytes, _t: str, description: str | None = None
    ):
        if value is None:
            print('WARN: ignored insert')
            return None

        if _t not in valid_types:
            raise ValueError('unsupported types has been used')

        # hash value
        m = hashlib.sha256()
        m.update(value)

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO server_variables
                            (id, key, description, value_type, value_data, value_hash)
                        VALUES
                            (%s::uuid, %s::varchar, %s, %s::varchar, %b, %s::varchar)
                        ON CONFLICT (key) DO UPDATE
                        SET
                            value_type = EXCLUDED.value_type,
                            value_data = EXCLUDED.value_data,
                            description = EXCLUDED.description,
                            updated_at = EXCLUDED.updated_at;
                        """,
                        [
                            uuid.uuid4(),
                            key.lower(),
                            description,
                            _t,
                            value,
                            m.hexdigest(),
                        ],
                    )
                except Exception as err:
                    print(err)
                    raise err


def get_keeper():
    conn = db.get_connection()
    assert not conn.closed
    return Keeper()
