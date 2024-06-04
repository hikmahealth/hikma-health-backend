from db_util import get_connection
import json
from patients.patient import Patient
from language_strings.data_access import update_language_string
from language_strings.language_string import to_id, LanguageString


def add_patient(patient: Patient):
    update_language_string(patient.given_name)
    update_language_string(patient.surname)
    update_language_string(patient.country)
    update_language_string(patient.hometown)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO patients (id, given_name, surname, date_of_birth, sex, country, hometown, phone, edited_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                        [patient.id,
                         to_id(patient.given_name),
                         to_id(patient.surname),
                         patient.date_of_birth,
                         patient.sex,
                         to_id(patient.country),
                         to_id(patient.hometown),
                         patient.phone,
                         patient.edited_at
                         ])


def patient_from_key_data(given_name: str, surname: str, country: str, sex: str):
    where_clauses = []
    params = []
    if given_name is not None:
        where_clauses.append("get_string(given_name, 'en') = %s")
        params.append(given_name)
    else:
        where_clauses.append("get_string(given_name, 'en') is null")

    if surname is not None:
        where_clauses.append("get_string(surname, 'en') = %s")
        params.append(surname)
    else:
        where_clauses.append("get_string(surname, 'en') is null")

    if country is not None:
        where_clauses.append("get_string(country, 'en') = %s")
        params.append(country)
    else:
        where_clauses.append("get_string(country, 'en') is null")

    if sex is not None:
        where_clauses.append("sex = %s")
        params.append(sex)
    else:
        where_clauses.append('sex is null')

    where_clause = ' AND '.join(where_clauses)

    query = f"SELECT id FROM patients WHERE {where_clause};"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            if row is None:
                return None
            return row[0]

def all_patient_data():
    # query = """
    # SELECT id, given_name, surname, date_of_birth, sex, citizenship, hometown, phone, edited_at FROM patients ORDER BY edited_at DESC LIMIT 25
    # """
    # Get the patient data from the patients column
    # FIXME add support for limit counts
    # query = """
    # SELECT id, 
    # given_name, 
    # surname, 
    # date_of_birth, 
    # sex, 
    # citizenship, 
    # hometown, 
    # phone, 
    # additional_data, 
    # government_id, 
    # external_patient_id, 
    # created_at, 
    # updated_at FROM patients ORDER BY updated_at DESC
    # """
    query = """
        SELECT
        JSON_BUILD_OBJECT(
            'id', p.id,
            'given_name', p.given_name, 
            'surname', p.surname, 
            'date_of_birth', p.date_of_birth, 
            'sex', p.sex, 
            'camp', p.camp,
            'citizenship', p.citizenship, 
            'hometown', p.hometown, 
            'phone', p.phone, 
            'additional_data', p.additional_data, 
            'government_id', p.government_id, 
            'external_patient_id', p.external_patient_id, 
            'created_at', p.created_at, 
            'updated_at', p.updated_at,
            'patient_additional_attributes', json_object_agg(COALESCE(pa.attribute_id::text, '_'::text), COALESCE(pa.string_value, pa.number_value::text, pa.boolean_value::text, pa.date_value::text))
        ) AS patient_data
        FROM patients p
        LEFT JOIN patient_additional_attributes pa ON p.id = pa.patient_id
        GROUP BY p.id, p.given_name, p.surname, p.date_of_birth, p.citizenship, p.created_at, p.updated_at;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [])
            results = cur.fetchall()
            patient_data = []
            for row in results:
                patient = row[0]
                # If not a valid JSON string, treat as empty dict
                additional_data = patient.get('additional_data', {})  
                patient_additional_attributes = patient.get('patient_additional_attributes', {})

                # Merge the two attribute dictionaries
                if patient_additional_attributes != {"_": None}:
                    merged_attributes = additional_data.copy() 
                    merged_attributes.update(patient_additional_attributes)
                    patient['additional_data'] = merged_attributes

                # Remove the original attribute fields
                # del patient['additional_data']
                del patient['patient_additional_attributes']

                patient_data.append(patient)

            return patient_data


# Given a patient_id get all their additional column values
def patient_additional_attributes(patient_id: str):
    query = """
        SELECT id, attribute_id, attribute, number_value, string_value, date_value, boolean_value
        FROM patient_additional_attributes
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.excecute(
                query, []
            )
            yield from cur

def search_patients(given_name: str, surname: str, country: str, hometown: str):
    where_clauses = []
    params = []
    if given_name is not None:
        where_clauses.append("UPPER(get_string(given_name, 'en')) LIKE %s")
        params.append(f'%{given_name.upper()}%')

    if surname is not None:
        where_clauses.append("UPPER(get_string(surname, 'en')) LIKE %s")
        params.append(f'%{surname.upper()}%')

    if country is not None:
        where_clauses.append("UPPER(get_string(country, 'en')) LIKE %s")
        params.append(f'%{country.upper()}%')

    if hometown is not None:
        where_clauses.append("UPPER(get_string(hometown, 'en')) LIKE %s")
        params.append(f'%{hometown.upper()}%')

    where_clause = ' AND '.join(where_clauses)

    query = f"SELECT id, given_name, surname, date_of_birth, sex, country, hometown, phone, edited_at FROM patients WHERE {where_clause};"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            yield from cur

def patient_from_id(patient_id):
    query = """
    SELECT given_name, surname, date_of_birth, sex, country, hometown, phone, edited_at FROM patients WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [patient_id])
            row = cur.fetchone()
            if row is None:
                return None
            given_name, surname, date_of_birth, sex, country, hometown, phone, edited_at = row
            return Patient(
                id=patient_id,
                given_name=LanguageString.from_id(given_name),
                surname=LanguageString.from_id(surname),
                date_of_birth=date_of_birth,
                sex=sex,
                country=LanguageString.from_id(country),
                hometown=LanguageString.from_id(hometown),
                phone=phone,
                edited_at=edited_at
            )

