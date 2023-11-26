from dataclasses import dataclass
from client_object import ClientObject
from datetime import datetime
from util import identity, parse_client_timestamp, parse_server_uuid, parse_client_bool

@dataclass
class Visit(ClientObject):
    id: str
    patient_id: str
    clinic_id: str
    provider_id: str
    check_in_timestamp: datetime
    edited_at: datetime
    deleted: bool

    def client_insert_values(self):
        return [self.id,
                self.patient_id,
                self.clinic_id,
                self.provider_id,
                self.format_ts(self.check_in_timestamp),
                self.format_ts(self.edited_at),
                self.format_bool(self.deleted)]

    @classmethod
    def client_insert_sql(cls):
        return """INSERT INTO visits (id, patient_id, clinic_id, provider_id, check_in_timestamp, edited_at, deleted) VALUES (?, ?, ?, ?, ?, ?, ?)"""

    def client_update_values(self):
        return [self.patient_id,
                self.clinic_id,
                self.provider_id,
                self.format_ts(self.check_in_timestamp),
                self.format_ts(self.edited_at),
                self.format_bool(self.deleted),
                self.id]

    @classmethod
    def client_update_sql(cls):
        return """UPDATE visits SET patient_id = ?, clinic_id = ?, provider_id = ?, check_in_timestamp = ?, edited_at = ?, deleted = ? WHERE id = ?"""

    def server_insert_values(self):
        return [self.id,
                self.patient_id,
                self.clinic_id,
                self.provider_id,
                self.check_in_timestamp,
                self.edited_at,
                self.deleted]

    @classmethod
    def server_insert_sql(cls):
        return """INSERT INTO visits (id, patient_id, clinic_id, provider_id, check_in_timestamp, edited_at, deleted) VALUES (%s, %s, %s, %s, %s, %s, %s)"""

    def server_update_values(self):
        return [self.patient_id,
                self.clinic_id,
                self.provider_id,
                self.check_in_timestamp,
                self.edited_at,
                self.deleted,
                self.id]

    @classmethod
    def server_update_sql(cls):
        return """UPDATE visits SET patient_id = %s, clinic_id = %s, provider_id = %s, check_in_timestamp = %s, edited_at = %s, deleted = %s WHERE id  = %s"""

    @classmethod
    def db_columns_from_server(cls):
        return [('id', lambda s: s.replace('-', '')),
                ('patient_id', parse_server_uuid),
                ('clinic_id', parse_server_uuid),
                ('provider_id', parse_server_uuid),
                ('check_in_timestamp', identity),
                ('edited_at', identity),
                ('deleted', identity)
        ]

    @classmethod
    def db_columns_from_client(cls):
        return [('id', identity),
                ('patient_id', identity),
                ('clinic_id', identity),
                ('provider_id', identity),
                ('check_in_timestamp', parse_client_timestamp),
                ('edited_at', parse_client_timestamp),
                ('deleted', parse_client_bool)
        ]

    @classmethod
    def table_name(cls):
        return "visits"
