from dataclasses import dataclass
from language_strings.language_string import LanguageString
from client_object import ClientObject
from datetime import datetime, date
from util import identity, parse_client_date, parse_client_timestamp


@dataclass
class Patient(ClientObject):
    id: str
    given_name: LanguageString
    surname: LanguageString
    date_of_birth: date
    sex: str
    country: LanguageString
    hometown: LanguageString
    phone: str
    additional_data: str
    # edited_at: datetime
    # start V2 migration
    government_id: str
    external_patient_id: str
    # end V2 migration
    created_at: datetime
    updated_at: datetime


    def client_insert_values(self):
        return [self.id,
                self.format_string(self.given_name),
                self.format_string(self.surname),
                self.format_date(self.date_of_birth),
                self.sex,
                self.format_string(self.country),
                self.format_string(self.hometown),
                self.government_id,
                self.external_patient_id,
                self.metadata,
                self.phone,
                self.format_ts(self.edited_at)]

    @classmethod
    def client_insert_sql(cls):
        return """INSERT INTO patients (id, given_name, surname, date_of_birth, sex, country, hometown, additional_data, phone, edited_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    def client_update_values(self):
        return [self.format_string(self.given_name),
                self.format_string(self.surname),
                self.format_date(self.date_of_birth),
                self.sex,
                self.format_string(self.country),
                self.format_string(self.hometown),
                self.phone,
                self.metadata,
                self.format_ts(self.edited_at),
                self.id]

    @classmethod
    def client_update_sql(cls):
        return """UPDATE patients SET given_name = ?, surname = ?, date_of_birth = ?, sex = ?, country = ?, hometown = ?, phone = ?, edited_at = ? WHERE id = ?"""
            

    def server_insert_values(self):
        return [self.id,
                self.format_string(self.given_name),
                self.format_string(self.surname),
                self.date_of_birth,
                self.sex,
                self.format_string(self.country),
                self.format_string(self.hometown),
                self.phone,
                self.metadata,
                self.edited_at]

    @classmethod
    def server_insert_sql(cls):
        return """INSERT INTO patients (id, given_name, surname, date_of_birth, sex, country, hometown, phone, edited_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

    def server_update_values(self):
        return [self.format_string(self.given_name),
                self.format_string(self.surname),
                self.date_of_birth,
                self.sex,
                self.format_string(self.country),
                self.format_string(self.hometown),
                self.phone,
                self.edited_at,
                self.metadata,
                self.id]

    @classmethod
    def server_update_sql(cls):
        return """UPDATE patients SET given_name = %s, surname = %s, date_of_birth = %s, sex = %s, country = %s, hometown = %s, phone = %s, edited_at = %s WHERE id = %s"""


    @classmethod
    def db_columns_from_server(cls):
        return [('id', lambda s: s.replace('-', '')),
                ('given_name', cls.make_language_string),
                ('surname', cls.make_language_string),
                ('date_of_birth', identity),
                ('sex', identity),
                ('country', cls.make_language_string),
                ('hometown', cls.make_language_string),
                ('phone', identity),
                ('additional_data', identity),
                ('edited_at', identity)]

    @classmethod
    def db_columns_from_client(cls):
        return [('id', identity),
                ('given_name', cls.make_language_string),
                ('surname', cls.make_language_string),
                ('date_of_birth', parse_client_date),
                ('sex', identity),
                ('country', cls.make_language_string),
                ('hometown', cls.make_language_string),
                ('phone', identity),
                ('additional_data', identity),
                ('edited_at', parse_client_timestamp)]

    @classmethod
    def table_name(cls):
        return "patients"

    @classmethod
    def from_db_row(cls, db_row):
        # id, given_name, surname, date_of_birth, sex, country, hometown, phone, edited_at = db_row
        # return cls(id, LanguageString.from_id(given_name), LanguageString.from_id(surname), date_of_birth, sex, LanguageString.from_id(country), LanguageString.from_id(hometown), phone, edited_at)
        id, given_name, surname, date_of_birth, sex, country, hometown, phone, additional_data, government_id, external_patient_id, created_at, updated_at = db_row
        return cls(id, given_name, surname, date_of_birth, sex, country, hometown, phone, additional_data, government_id, external_patient_id, created_at, updated_at)

    # def to_dict(self):
    #     return {
    #         'id': self.id,
    #         'given_name': self.given_name.to_dict() if self.given_name is not None else None,
    #         'surname': self.surname.to_dict() if self.surname is not None else None,
    #         'date_of_birth': self.date_of_birth,
    #         'sex': self.sex,
    #         'country': self.country.to_dict() if self.country is not None else None,
    #         'hometown': self.hometown.to_dict() if self.hometown is not None else None,
    #         'phone': self.phone,
    #         'edited_at': self.edited_at
    #     }

    def to_dict(self):
        return {
            'id': self.id,
            'given_name': self.given_name,
            'surname': self.surname,
            'date_of_birth': self.date_of_birth,
            'sex': self.sex,
            'country': self.country,
            'hometown': self.hometown,
            'phone': self.phone,
            'additional_data': self.additional_data,
            'created_at': self.created_at,
            'updated_at': self.updated_at,

            #v2
            'external_patient_id': self.external_patient_id,
            'government_id': self.government_id
        }
