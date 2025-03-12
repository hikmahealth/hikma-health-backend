###############################################################
# CUSTOM ADMIN ROUTES ARE DEFINED IN THIS FILE
# THIS COULD SIMPLIFY KEEPING YOUR CODE UP TO DATE WITH
# UPSTREAM CHANGES

# HIKMA HEALTH UPSTREAM WILL FOCUS ON UPDATING THE
# `routes_admin.py` FILE.

# ⭐️ If you need to add a new route, add it here ⭐️
###############################################################

from datetime import datetime, timezone
import logging
from flask import Blueprint, request, jsonify

from hikmahealth.server.routes_admin import api

from hikmahealth.server.api import middleware, auth
from hikmahealth.server.client import db
from hikmahealth.server.helpers import web as webhelper

from hikmahealth.entity import hh
import hikmahealth.entity.fields as f

from hikmahealth.utils.misc import convert_dict_keys_to_snake_case, convert_operator
from hikmahealth.utils.errors import WebError
from psycopg import Error as PostgresError
from sqlalchemy import select, func, case, text

from datetime import datetime, date
from dataclasses import dataclass, asdict
import dataclasses

from typing import Any
import json

import uuid
import bcrypt

from psycopg.rows import dict_row, class_row
import psycopg.errors

from urllib import parse as urlparse

from hikmahealth.utils.datetime import utc
from psycopg import sql


@api.route('/dashboard/kpis', methods=['POST'])
@middleware.authenticated_admin
def get_kpis(_):
	if not request.is_json:
		return jsonify({'error': 'Request must be JSON'}), 400

	data = request.get_json()
	start_date = data.get('start_date')
	end_date = data.get('end_date')
	kpi_fields = data.get('kpi_fields')

	if not all([start_date, end_date, kpi_fields]):
		return jsonify({'error': 'Missing required fields'}), 400

	patient_fields = kpi_fields.get('patient_fields', [])
	event_fields = kpi_fields.get('event_fields', {})

	response = {'patient_field_counts': {}, 'event_field_counts': {}}

	print('patient fields')

	# get the valid patient fields
	patient_columns = hh.Patient.filter_valid_colums(patient_fields)
	patient_attribute_columns = set(patient_fields) - set(patient_columns)

	print('valid fields')
	print(patient_columns)

	with db.get_connection() as conn:
		with conn.cursor(row_factory=dict_row) as cur:
			# Get patient field counts
			if len(patient_columns) > 0:
				for field in patient_columns:
					# Direct column query
					query = sql.SQL("""
                        WITH field_values AS (
                            SELECT {field} as value
                            FROM patients p
                            WHERE p.is_deleted = false
                            AND p.created_at >= %s
                            AND p.created_at <= %s
                        )
                        SELECT value::text, COUNT(*) as count
                        FROM field_values
                        WHERE value IS NOT NULL
                        GROUP BY value
                    """).format(field=sql.Identifier(field))

					cur.execute(query, (start_date, end_date))

					counts = {}
					for row in cur.fetchall():
						try:
							value = row['value']
							# Handle potential JSON string values
							if value.startswith('"') and value.endswith('"'):
								value = value[1:-1]
							counts[value] = row['count']
						except Exception as e:
							logging.error(f'Error processing patient field value: {e}')
							continue

					response['patient_field_counts'][field] = counts

			# Get patient attribute field counts
			if len(patient_attribute_columns) > 0:
				for field in patient_attribute_columns:
					# EAV query
					# get all the attribute entries where the attribute_id column is one of the patient_attribute_columns
					cur.execute(
						"""
                        WITH field_values AS (
                            SELECT pa.attribute_id,
                                COALESCE(pa.string_value, 
                                         CAST(pa.number_value AS TEXT),
                                         CAST(pa.boolean_value AS TEXT),
                                         CAST(pa.date_value AS TEXT)) as value
                            FROM patient_additional_attributes pa
                            WHERE pa.attribute_id = %s
                            AND pa.is_deleted = false
                            AND pa.created_at >= %s
                            AND pa.created_at <= %s
                        )
                        SELECT value::text, COUNT(*) as count
                        FROM field_values
                        WHERE value IS NOT NULL
                        GROUP BY value
                    """,
						(field, start_date, end_date),
					)

					counts = {}
					for row in cur.fetchall():
						try:
							value = row['value']
							# Handle potential JSON string values
							if value.startswith('"') and value.endswith('"'):
								value = value[1:-1]
							counts[value] = row['count']
						except Exception as e:
							logging.error(
								f'Error processing patient attribute field value: {e}'
							)
							continue

					response['patient_field_counts'][field] = counts

			# Get event field counts
			for form_id, field_ids in event_fields.items():
				response['event_field_counts'][form_id] = {}

				for field_id in field_ids:
					query = sql.SQL("""
                        SELECT e.form_data, e.form_id
                        FROM events e
                        WHERE e.form_id = %s
                        AND e.is_deleted = false
                        AND e.created_at >= %s
                        AND e.created_at <= %s
                    """)
					cur.execute(query, (form_id, start_date, end_date))
					results = cur.fetchall()

					counts = {}
					for row in results:
						form_data = row['form_data']

						relevant_fields = filter(
							lambda x: x['fieldId'] == field_id, form_data
						)

						for field in relevant_fields:
							try:
								value = field['value']
								# Handle potential JSON string values
								if value.startswith('"') and value.endswith('"'):
									value = value[1:-1]
								counts[value] = counts.get(value, 0) + 1
							except Exception as e:
								logging.error(
									f'Error processing event field value: {e}'
								)
								continue

					response['event_field_counts'][form_id][field_id] = counts

	return jsonify(response)
