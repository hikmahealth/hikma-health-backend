from flask import jsonify
import time
from datetime import timezone, datetime
import pytz


from hikmahealth.server.client.db import get_connection


def getNthTimeSyncData(timestamp):
	is_not_deleted_str = ' AND is_deleted = false'
	is_deleted_str = ' AND is_deleted = true'

	events_new, events_updated, events_deleted = fetch_records(
		get_connection(), 'events', timestamp
	)

	patients_new, patients_updated, patients_deleted = fetch_records(
		get_connection(), 'patients', timestamp
	)

	# patient attributes EAV table: shortened name of "patient_additional_attributes"
	patient_attributes_new, patient_attributes_updated, patient_attributes_deleted = (
		fetch_records(get_connection(), 'patient_additional_attributes', timestamp)
	)

	clinics_new, clinics_updated, clinics_deleted = fetch_records(
		get_connection(), 'clinics', timestamp
	)

	visits_new, visits_updated, visits_deleted = fetch_records(
		get_connection(), 'visits', timestamp
	)

	string_ids_new, string_ids_updated, string_ids_deleted = fetch_records(
		get_connection(), 'string_ids', timestamp
	)

	string_content_new, string_content_updated, string_content_deleted = fetch_records(
		get_connection(), 'string_content', timestamp
	)

	event_forms_new, event_forms_updated, event_forms_deleted = fetch_records(
		get_connection(), 'event_forms', timestamp
	)

	(
		patient_registration_forms_new,
		patient_registration_forms_updated,
		patient_registration_forms_deleted,
	) = fetch_records(get_connection(), 'patient_registration_forms', timestamp)

	appointments_new, appointments_updated, appointments_deleted = fetch_records(
		get_connection(), 'appointments', timestamp
	)

	return (
		(events_new, events_updated, events_deleted),
		(patients_new, patients_updated, patients_deleted),
		(
			patient_attributes_new,
			patient_attributes_updated,
			patient_attributes_deleted,
		),
		(clinics_new, clinics_updated, clinics_deleted),
		(visits_new, visits_updated, visits_deleted),
		(string_ids_new, string_ids_updated, string_ids_deleted),
		(string_content_new, string_content_updated, string_content_deleted),
		(event_forms_new, event_forms_updated, event_forms_deleted),
		(
			patient_registration_forms_new,
			patient_registration_forms_updated,
			patient_registration_forms_deleted,
		),
		(appointments_new, appointments_updated, appointments_deleted),
	)


def fetch_records(conn, table, timestamp):
	"""
	Fetches new, updated, and deleted records from the specified table based on the given timestamp.

	Args:
	    conn: The database connection object.
	    table: The name of the table to fetch records from.
	    timestamp: The timestamp to compare against for fetching records.

	Returns:
	    A tuple containing three lists:
	    - new_records: A list of new records fetched from the table.
	    - updated_records: A list of updated records fetched from the table.
	    - deleted_records: A list of IDs of deleted records fetched from the table.
	"""
	with conn.cursor() as cur:
		# Fetch new records
		cur.execute(
			'SELECT * FROM {} WHERE server_created_at > %s AND deleted_at IS NULL'.format(
				table
			),
			(timestamp,),
		)
		new_records = cur.fetchall()
		new_records = [
			dict(zip([column[0] for column in cur.description], row))
			for row in new_records
		]

		# Fetch updated records
		cur.execute(
			'SELECT * FROM {} WHERE last_modified > %s AND server_created_at < %s AND deleted_at IS NULL'.format(
				table
			),
			(timestamp, timestamp),
		)
		updated_records = cur.fetchall()
		updated_records = [
			dict(zip([column[0] for column in cur.description], row))
			for row in updated_records
		]

		# Fetch deleted records
		cur.execute(
			'SELECT id FROM {} WHERE deleted_at > %s'.format(table),
			(timestamp,),
		)
		deleted_records = cur.fetchall()
		deleted_records = [row[0] for row in deleted_records]

	return new_records, updated_records, deleted_records


# data = { "patients": { "created": [], "updated": [], "deleted": [] }, "events": {}, "visits": {}, "users": {}, "clinics": "" }
def apply_edge_changes(data, lastPulledAt):
	# patients
	patients = data['patients']
	patient_additional_attributes = data['patient_additional_attributes']
	events = data['events']
	visits = data['visits']
	# Function ignores the patient_registration_forms because they are server made only

	appointments = data['appointments']

	with get_connection() as conn:
		with conn.cursor() as cur:
			try:
				apply_edge_patient_changes(patients, cur, lastPulledAt)
				conn.commit()
			except Exception as e:
				conn.rollback()
				print('Error while executing SQL commands: ', e)
				raise e

			try:
				apply_edge_patient_attribute_changes(
					patient_additional_attributes, cur, lastPulledAt
				)
				conn.commit()
			except Exception as e:
				conn.rollback()
				print('Error while executing SQL commands: ', e)
				raise e

			try:
				apply_edge_visits_changes(visits, cur, lastPulledAt)
				conn.commit()
			except Exception as e:
				conn.rollback()
				print('Error while executing SQL commands: ', e)
				raise e

			try:
				apply_edge_event_changes(events, cur, lastPulledAt)
				conn.commit()
			except Exception as e:
				conn.rollback()
				print('Error while executing SQL commands: ', e)
				raise e

			try:
				apply_edge_appointment_changes(appointments, cur, lastPulledAt)
				conn.commit()
			except Exception as e:
				conn.rollback()
				print('Error while executing SQL commands: ', e)
				raise e


# Function that takes the results of getNthTimeSyncData and formats them into a JSON object to be returned to the client
def formatGETSyncResponse(syncData):
	(
		events,
		patients,
		patient_additional_attributes,
		clinics,
		visits,
		string_ids,
		string_content,
		event_forms,
		patient_registration_forms,
		appointments,
	) = syncData
	return jsonify(
		{
			'changes': {
				'events': {
					'created': events[0],
					'updated': events[1],
					'deleted': events[2],
				},
				'patients': {
					'created': patients[0],
					'updated': patients[1],
					'deleted': patients[2],
				},
				'patient_additional_attributes': {
					'created': patient_additional_attributes[0],
					'updated': patient_additional_attributes[1],
					'deleted': patient_additional_attributes[2],
				},
				'clinics': {
					'created': clinics[0],
					'updated': clinics[1],
					'deleted': clinics[2],
				},
				'visits': {
					'created': visits[0],
					'updated': visits[1],
					'deleted': visits[2],
				},
				'string_ids': {
					'created': string_ids[0],
					'updated': string_ids[1],
					'deleted': string_ids[2],
				},
				'string_content': {
					'created': string_content[0],
					'updated': string_content[1],
					'deleted': string_content[2],
				},
				'event_forms': {
					'created': event_forms[0],
					'updated': event_forms[1],
					'deleted': event_forms[2],
				},
				'registration_forms': {
					'created': patient_registration_forms[0],
					'updated': patient_registration_forms[1],
					'deleted': patient_registration_forms[2],
				},
				'appointments': {
					'created': appointments[0],
					'updated': appointments[1],
					'deleted': appointments[2],
				},
			},
			'timestamp': get_timestamp_now(),
		}
	)


def apply_edge_patient_changes(patients, cur, lastPulledAt):
	# CREATED PATIENTS
	if len(patients['created']) > 0:
		patient_insert = """INSERT INTO patients (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, government_id, external_patient_id, created_at, updated_at)"""
		patients_sql = [
			(
				patient['id'],
				patient['given_name'],
				patient['surname'],
				patient['date_of_birth'],
				patient['citizenship'],
				patient['hometown'],
				patient['sex'],
				patient['phone'],
				patient['camp'],
				patient['additional_data'],
				# V2 migration on app
				patient['government_id'],
				patient['external_patient_id'],
				date_from_timestamp(patient['created_at']),
				date_from_timestamp(patient['updated_at']),
			)
			for patient in patients['created']
		]

		args = ','.join(
			cur.mogrify(
				'(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', i
			).decode('utf-8')
			for i in patients_sql
		)
		cur.execute(patient_insert + ' VALUES ' + (args))

	# UPDATED PATIENTS
	# UPDATE patients SET name = 'new name' WHERE id = 'id'
	for patient in patients['updated']:
		cur.execute(
			f"""INSERT INTO patients (id, given_name, surname, date_of_birth, citizenship, hometown, sex, phone, camp, additional_data, government_id, external_patient_id, created_at, updated_at, last_modified)
                VALUES ('{patient['id']}', '{patient['given_name']}', '{patient['surname']}', '{patient['date_of_birth']}', '{patient['citizenship']}', '{patient['hometown']}', '{patient['sex']}',
                        '{patient['phone']}', '{patient['camp']}', '{patient['additional_data']}', '{patient['government_id']}', '{patient['external_patient_id']}', '{date_from_timestamp(patient['created_at'])}', '{date_from_timestamp(patient['updated_at'])}', '{datetime.now()}')
                ON CONFLICT (id) DO UPDATE
                SET given_name = EXCLUDED.given_name,
                    surname = EXCLUDED.surname,
                    date_of_birth = EXCLUDED.date_of_birth,
                    citizenship = EXCLUDED.citizenship,
                    hometown = EXCLUDED.hometown,
                    sex = EXCLUDED.sex,
                    phone = EXCLUDED.phone,
                    camp = EXCLUDED.camp,
                    additional_data = EXCLUDED.additional_data,
                    government_id = EXCLUDED.government_id,
                    external_patient_id = EXCLUDED.external_patient_id,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at,
                    last_modified = EXCLUDED.last_modified;
            """
		)

	# DELETED PATIENTS
	for patient in patients['deleted']:
		# if len(patients["deleted"]) > 0:
		# convert array of strings to tuple of strings
		# deleted_ids = tuple(patients["deleted"])
		# cur.execute(f"""DELETE FROM patients WHERE id IN ({deleted_ids});""")
		cur.execute(
			f"""UPDATE patients SET is_deleted=true, deleted_at='{
				date_from_timestamp(lastPulledAt)
			}' WHERE id = '{patient}';"""
		)


### PATIENT ADDITIONAL ATTRIBUTES
def apply_edge_patient_attribute_changes(patient_attributes, cur, lastPulledAt):
	# CREATED PATIENT ADDITIONAL ATTRIBUTES
	if len(patient_attributes['created']) > 0:
		patient_insert = """INSERT INTO patient_additional_attributes (
        id,
        patient_id,
        attribute_id,
        attribute,
        number_value,
        string_value,
        date_value,
        boolean_value,
        metadata,
        is_deleted,
        created_at, 
        updated_at,
        last_modified,
        server_created_at
        )"""
		patient_attributes_sql = [
			(
				patient_attribute['id'],
				patient_attribute['patient_id'],
				patient_attribute['attribute_id'],
				patient_attribute['attribute'],
				patient_attribute['number_value'],
				patient_attribute['string_value'],
				to_timestamptz(patient_attribute['date_value']),
				patient_attribute['boolean_value'],
				patient_attribute['metadata'],
				False,
				date_from_timestamp(patient_attribute['created_at']),
				date_from_timestamp(patient_attribute['updated_at']),
				datetime.now(),
				datetime.now(),
			)
			for patient_attribute in patient_attributes['created']
		]

		args = ','.join(
			cur.mogrify(
				'(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', i
			).decode('utf-8')
			for i in patient_attributes_sql
		)
		cur.execute(patient_insert + ' VALUES ' + (args))

	# UPDATED PATIENT ADDITIONAL ATTRIBUTES
	for patient_attribute in patient_attributes['updated']:
		cur.execute(
			f"""INSERT INTO patient_additional_attributes (
                id,
                patient_id,
                attribute_id,
                attribute,
                number_value,
                string_value,
                date_value,
                boolean_value,
                metadata,
                is_deleted,
                created_at, 
                updated_at
                last_modified,
                server_created_at,
            )
                VALUES (
                        '{patient_attribute['id']}', 
                        '{patient_attribute['patient_id']}',
                        '{patient_attribute['attribute_id']}',
                        '{patient_attribute['attribute']}',
                        '{patient_attribute['number_value']}',
                        '{patient_attribute['string_value']}',
                        '{patient_attribute['date_value']}',
                        '{patient_attribute['boolean_value']}',
                        '{patient_attribute['metadata']}',                       
                        '{False}',
                        '{date_from_timestamp(patient['created_at'])}', 
                        '{date_from_timestamp(patient['updated_at'])}', 
                        '{datetime.now()}',
                        '{datetime.now()}')
                ON CONFLICT (id) DO UPDATE
                SET 
                    patient_id = EXCLUDED.patient_id,
                    attribute_id = EXCLUDED.attribute_id,
                    attribute = EXCLUDED.attribute,
                    number_value = EXCLUDED.number_value,
                    string_value = EXCLUDED.string_value,
                    date_value = EXCLUDED.date_value,
                    boolean_value = EXCLUDED.boolean_value,
                    metadata = EXCLUDED.metadata,
                                   
                    updated_at = EXCLUDED.updated_at,
                    last_modified = EXCLUDED.last_modified;
            """
		)

	# DELETED PATIENT ADDITIONAL ATTRIBUTES
	for patient_attribute in patient_attributes['deleted']:
		# if len(patient_additional_attributes["deleted"]) > 0:
		# convert array of strings to tuple of strings
		# deleted_ids = tuple(patient_attribute["deleted"])
		# cur.execute(f"""DELETE FROM patient_additional_attributes WHERE id IN ({deleted_ids});""")
		cur.execute(
			f"""UPDATE patient_additional_attributes SET is_deleted=true, deleted_at='{
				date_from_timestamp(lastPulledAt)
			}' WHERE id = '{patient_attribute}';"""
		)


def apply_edge_event_changes(events, cur, lastPulledAt):
	# CREATED EVENTS
	if len(events['created']) > 0:
		event_insert = 'INSERT INTO events (id, patient_id, form_id, visit_id, event_type, form_data, metadata, is_deleted, created_at, updated_at) VALUES '
		events_sql = [
			(
				event['id'],
				event['patient_id'],
				event['form_id'],
				event['visit_id'],
				event['event_type'],
				event['form_data'],
				event['metadata'],
				event['is_deleted'],
				date_from_timestamp(event['created_at']),
				date_from_timestamp(event['updated_at']),
			)
			for event in events['created']
		]

		# print("EVENTS SQL: ", events_sql)

		args = ','.join(
			cur.mogrify('(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', i).decode('utf-8')
			for i in events_sql
		)
		cur.execute(event_insert + (args))

	# UPDATED EVENTS
	# UPDATE events SET name = 'new name' WHERE id = 'id'
	for event in events['updated']:
		cur.execute(
			f"""UPDATE events SET patient_id='{event['patient_id']}', form_id='{
				event['form_id']
			}', visit_id='{event['visit_id']}', event_type='{
				event['event_type']
			}', form_data='{event['form_data']}', metadata='{
				event['metadata']
			}', is_deleted='{event['is_deleted']}', created_at='{
				date_from_timestamp(event['created_at'])
			}', updated_at='{
				date_from_timestamp(event['updated_at'])
			}', last_modified='{datetime.now()}' WHERE id='{event['id']}';"""
		)

	# DELETED EVENTS
	# if len(events["deleted"]) > 0:
	for event in events['deleted']:
		# deleted_ids = tuple(events["deleted"])
		# cur.execute(f"""DELETE FROM events WHERE id IN ({deleted_ids});""")
		cur.execute(
			f"""UPDATE events SET is_deleted=true, deleted_at='{
				date_from_timestamp(lastPulledAt)
			}' WHERE id = '{event}';"""
		)


def apply_edge_visits_changes(visits, cur, lastPulledAt):
	# CREATED VISITS
	if len(visits['created']) > 0:
		visit_insert = 'INSERT INTO visits (id, patient_id, clinic_id, provider_id, provider_name, check_in_timestamp, is_deleted, metadata, created_at, updated_at) VALUES '
		visits_sql = [
			(
				visit['id'],
				visit['patient_id'],
				visit['clinic_id'],
				visit['provider_id'],
				visit['provider_name'],
				date_from_timestamp(visit['check_in_timestamp']),
				visit['is_deleted'],
				visit['metadata'],
				date_from_timestamp(visit['created_at']),
				date_from_timestamp(visit['updated_at']),
			)
			for visit in visits['created']
		]

		args = ','.join(
			cur.mogrify('(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', i).decode('utf-8')
			for i in visits_sql
		)
		cur.execute(visit_insert + (args))

	# UPDATED VISITS
	# UPDATE visits SET name = 'new name' WHERE id = 'id'
	for visit in visits['updated']:
		cur.execute(
			f"""UPDATE visits SET patient_id='{visit['patient_id']}', clinic_id='{
				visit['clinic_id']
			}', provider_id='{visit['provider_id']}', provider_name='{
				visit['provider_name']
			}', check_in_timestamp='{visit['check_in_timestamp']}', is_deleted='{
				visit['is_deleted']
			}', metadata='{visit['metadata']}', created_at='{
				date_from_timestamp(visit['created_at'])
			}', updated_at='{
				date_from_timestamp(visit['updated_at'])
			}' , last_modified='{datetime.now()}' WHERE id='{visit['id']}';"""
		)

	# DELETED VISITS
	for visit in visits['deleted']:
		# deleted_ids = tuple(visits["deleted"])
		# cur.execute(f"""DELETE FROM visits WHERE id IN {deleted_ids};""")
		cur.execute(
			f"""UPDATE visits SET is_deleted=true, deleted_at='{
				date_from_timestamp(lastPulledAt)
			}' WHERE id = '{visit}';"""
		)


# TODO: Move to utils
def date_from_timestamp(timestamp):
	date = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
	return date


def get_timestamp_now():
	return time.mktime(datetime.now().timetuple()) * 1000


# function to convert a javascript timestamp into a datetime object at gmt time
def convert_timestamp_to_gmt(timestamp):
	# convert the lastPuledAt milliseconds string into a date object of gmt time
	return datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)


def to_timestamptz(value):
	if isinstance(value, (int, float)):
		# Assuming the number is a milliseconds Unix timestamp
		return datetime.fromtimestamp(value / 1000.0, pytz.UTC)
	elif isinstance(value, str):
		# Assuming the string is in a standard datetime format
		try:
			return datetime.fromisoformat(value).astimezone(pytz.UTC)
		except ValueError:
			# Handle other string formats if necessary
			return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').astimezone(pytz.UTC)
	return None


def apply_edge_appointment_changes(appointments, cur, lastPulledAt):
	# CREATED APPOINTMENTS
	if len(appointments['created']) > 0:
		appointment_insert = 'INSERT INTO appointments (id, appointment_timestamp, duration, reason, notes, provider_id, clinic_id, patient_id, user_id, status, current_visit_id, fufilled_visit_id, metadata, created_at, updated_at, is_deleted) VALUES '
		appointments_sql = [
			(
				appointment['id'],
				date_from_timestamp(appointment['appointment_timestamp']),
				appointment['duration'],
				appointment['reason'],
				appointment['notes'],
				appointment['provider_id'],
				appointment['clinic_id'],
				appointment['patient_id'],
				appointment['user_id'],
				appointment['status'],
				appointment['current_visit_id'],
				appointment['fufilled_visit_id'],
				appointment['metadata'],
				date_from_timestamp(appointment['created_at']),
				date_from_timestamp(appointment['updated_at']),
				appointment['is_deleted'],
			)
			for appointment in appointments['created']
		]

		args = ','.join(
			cur.mogrify('(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', i).decode(
				'utf-8'
			)
			for i in appointments_sql
		)
		cur.execute(appointment_insert + (args))

	# UPDATED appointmentS
	# UPDATE appointments SET name = 'new name' WHERE id = 'id'
	for appointment in appointments['updated']:
		cur.execute(
			f"""UPDATE appointments SET appointment_timestamp='{
				date_from_timestamp(appointment['appointment_timestamp'])
			}', duration='{appointment['duration']}', reason='{
				appointment['reason']
			}', notes='{appointment['notes']}', provider_id='{
				appointment['provider_id']
			}', clinic_id='{appointment['clinic_id']}', patient_id='{
				appointment['patient_id']
			}', user_id='{appointment['user_id']}', status='{
				appointment['status']
			}' , current_visit_id='{
				appointment['current_visit_id']
			}' , fufilled_visit_id='{appointment['fufilled_visit_id']}' , metadata='{
				appointment['metadata']
			}' ,
                created_at='{
				date_from_timestamp(appointment['created_at'])
			}' , updated_at='{
				date_from_timestamp(appointment['updated_at'])
			}', last_modified='{datetime.now()}' WHERE id='{appointment['id']}';"""
		)

	# DELETED appointmentS
	for appointment in appointments['deleted']:
		# deleted_ids = tuple(appointments["deleted"])
		# cur.execute(f"""DELETE FROM appointments WHERE id IN {deleted_ids};""")
		cur.execute(
			f"""UPDATE appointments SET is_deleted=true, deleted_at='{
				date_from_timestamp(lastPulledAt)
			}' WHERE id = '{appointment}';"""
		)
