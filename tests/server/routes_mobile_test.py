from datetime import datetime
import pytest
from flask import url_for
import uuid
from tests.conftest import test_email, test_password


def test_hello_world(client):
	"""Test the hello world endpoint."""
	response = client.get('/')
	assert response.status_code == 200
	assert b'Welcome to the Hikma Health backend' in response.data


def test_login(client):
	"""Test the login endpoint."""
	# Test with invalid credentials
	response = client.post(
		'/v1/api/login', json={'email': 'test@hikmah.com', 'password': 'test'}
	)
	assert response.status_code == 404  # Unauthorized

	# Test with valid credentials (assuming these exist in your test database)
	response = client.post(
		'/v1/api/login', json={'email': test_email, 'password': test_password}
	)
	assert response.status_code == 200
	assert 'id' in response.json  # User dictionary should contain an ID
	assert 'email' in response.json

	assert response.json['email'] == test_email


#### Sync tests
# Must test push and pull enpoints
# Tables involved are:
#   - Patients (pushed from client, pulled from server)
#   - PatientAdditionalAttributes (pushed from client, pulled from server)
#   - Visits (pushed from client, pulled from server)
#   - Events (pushed from client, pulled from server)
#   - Appointments (pushed from client, pulled from server)
#   - Prescriptions (pushed from client, pulled from server)
#   - StringIds (ignored)
#   - StringContent (ignored)
#   - EventForms (pulled from server)
#   - PatientRegistrationForms (pulled from server)
#   - Clinics (pulled from server)
#   - Users (pulled from server)


# Edge cases:
#   - Invalid email and password combination during sync
#   - Attempting to sync records with a patient_id that does not exist in the patients table (these could be events, visits, appointments, prescriptions)
#
# Tests must be able to sync


class TestSync:
	def test_invalid_auth_during_sync(self, client, test_db):
		# Test invalid credentials
		response = client.post(
			'/api/sync/v2/pull',
			headers={'Authorization': 'Basic invalid_creds'},
			json={},
		)
		assert response.status_code != 200

	## TEST works, just needs to be re-thought. underlying assumtions of creating patient records on demand to prevent sync failures needs another thought.
	# def test_missing_patient_references(self, client, test_db, auth_headers):
	#     # Test pushing events with non-existent patient
	#     non_existent_patient_id = uuid.uuid4()
	#     non_existent_visit_id = uuid.uuid4()
	#     non_existent_form_id = uuid.uuid4()
	#     sync_data = {
	#         "events": {
	#             "created": [{
	#             "id": uuid.uuid4(),
	#             "patient_id": non_existent_patient_id,
	#             "visit_id": non_existent_visit_id,
	#             "form_id": non_existent_form_id,
	#             "event_type": "test_type",
	#             "event_timestamp": "2025-01-29T13:27:06Z",
	#             "form_data": "[]",
	#             "metadata": "{}",
	#             "created_at": datetime.now(),
	#             "updated_at": datetime.now()
	#         }]}
	#     }
	#     print("auth_headeers")
	#     print(auth_headers)

	#     # for pushes the last_pulled_at does not matter so much
	#     lastPulledAt = 0
	#     response = client.post(f'/v1/api/sync?last_pulled_at={lastPulledAt}',
	#         headers=auth_headers,
	#         json=sync_data)
	#     assert response.status_code == 400
	#     assert "patient_id not found" in response.json["message"]

	# def test_concurrent_sync(self, client, test_db, auth_headers):
	#     # Test multiple syncs with same data
	#     import threading
	#     import queue

	#     results = queue.Queue()

	#     def sync_worker():
	#         response = client.post('/api/sync/v2/pull',
	#             headers=auth_headers,
	#             json={})
	#         results.put(response.status_code)

	#     threads = [threading.Thread(target=sync_worker) for _ in range(5)]
	#     for t in threads:
	#         t.start()
	#     for t in threads:
	#         t.join()

	#     # Verify all syncs completed successfully
	#     while not results.empty():
	#         assert results.get() == 200

	# def test_large_dataset_sync(self, client, test_db, auth_headers):
	#     # Test sync with large number of records
	#     large_dataset = {
	#         "patients": [
	#             {
	#                 "id": f"patient_{i}",
	#                 "given_name": f"Test{i}",
	#                 "surname": f"Patient{i}",
	#                 "date_of_birth": "2000-01-01"
	#             } for i in range(1000)
	#         ]
	#     }
	#     response = client.post('/api/sync/v2/push',
	#         headers=auth_headers,
	#         json=large_dataset)
	#     assert response.status_code == 200

	# def test_partial_sync_recovery(self, client, test_db, auth_headers):
	#     # Test sync recovery after interruption
	#     first_batch = {
	#         "patients": [
	#             {
	#                 "id": "patient_1",
	#                 "given_name": "Test",
	#                 "surname": "Patient",
	#                 "date_of_birth": "2000-01-01"
	#             }
	#         ]
	#     }
	#     response = client.post('/api/sync/v2/push',
	#         headers=auth_headers,
	#         json=first_batch)
	#     assert response.status_code == 200

	#     # Simulate interrupted sync with more data
	#     second_batch = {
	#         "visits": [
	#             {
	#                 "id": "visit_1",
	#                 "patient_id": "patient_1",
	#                 "visit_timestamp": "2025-01-29T13:27:06Z"
	#             }
	#         ]
	#     }
	#     response = client.post('/api/sync/v2/push',
	#         headers=auth_headers,
	#         json=second_batch)
	#     assert response.status_code == 200

	# def test_timestamp_handling(self, client, test_db, auth_headers):
	#     # Test various timestamp scenarios
	#     timestamps = [
	#         "2025-01-29T13:27:06Z",  # UTC
	#         "2025-01-29T13:27:06+00:00",  # ISO with timezone
	#         "1706563626",  # Unix timestamp
	#         None,  # Missing timestamp
	#     ]

	#     for ts in timestamps:
	#         response = client.get('/api/sync/v2/pull',
	#             headers=auth_headers,
	#             query_string={'last_pulled_at': ts} if ts else {})
	#         assert response.status_code == 200
