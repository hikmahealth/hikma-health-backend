import os
import pytest
from flask import Flask
from hikmahealth.server.server import app as create_app
import psycopg
from dotenv import load_dotenv

load_dotenv('../../app/.env', verbose=True, override=True)
load_dotenv('../../.env', verbose=True, override=True)


test_email = os.getenv('TEST_EMAIL')
test_password = os.getenv('TEST_PASSWORD')


@pytest.fixture
def app():
	"""Create and configure a new app instance for each test."""
	app = create_app
	app.config.update(
		{
			'TESTING': True,
		}
	)
	yield app


@pytest.fixture
def client(app):
	"""A test client for the app."""
	return app.test_client()


@pytest.fixture
def runner(app):
	"""A test runner for the app's Click commands."""
	return app.test_cli_runner()


@pytest.fixture
def auth_headers():
	"""Provide authentication headers for test requests"""
	import base64

	# Create basic auth header
	credentials = f'{test_email}:{test_password}'
	encoded_credentials = base64.b64encode(credentials.encode()).decode()

	return {
		'Authorization': f'Basic {encoded_credentials}',
		'Content-Type': 'application/json',
	}


@pytest.fixture(scope='session')
def test_db():
	"""
	Connect to the remote test database specified in .env
	This fixture has session scope, so the connection persists for the entire test session.
	"""
	database_url = os.getenv('DATABASE_URL')
	print(
		'Connecting to database:', database_url.split('@')[1].split('/')[0]
	)  # Only print host/db info, not credentials

	if not database_url:
		pytest.skip('DATABASE_URL not set in .env file')

	try:
		# Connect to the remote database
		conn = psycopg.connect(database_url)
		yield conn
		conn.close()
	except psycopg.OperationalError as e:
		pytest.skip(f'Could not connect to remote database: {str(e)}')
	except Exception as e:
		pytest.skip(f'Unexpected error connecting to database: {str(e)}')
