from __future__ import annotations
import bcrypt

from hikmahealth.server.client import db
from hikmahealth.utils.errors import WebError

from hikmahealth.entity import core

import bcrypt
from psycopg.rows import dict_row

import uuid


@core.dataentity
class User(core.Entity):
	id: str
	name: str
	role: str
	email: str
	clinic_id: str


def create_session_token(u: User):
	with db.get_connection() as conn:
		with conn.cursor() as cur:
			token = str(uuid.uuid4())
			cur.execute(
				"""
                INSERT INTO tokens 
                (user_id, token)
                VALUES
                (%s, %s)
                RETURNING token
                """,
				(u.id, token),
			)

	return token


def invalidate_tokens(u: User):
	with db.get_connection() as conn:
		with conn.cursor() as cur:
			cur.execute('DELETE FROM tokens WHERE user_id = %s', [u.id])


def get_user_from_token(token: str) -> User:
	with db.get_connection() as conn:
		with conn.cursor(row_factory=dict_row) as cur:
			res = cur.execute(
				'SELECT user_id FROM tokens WHERE token = %s AND expiry > now()',
				(token,),
			).fetchone()

			if res is None:
				# log here
				raise WebError('invalid authentication token', 401)

			urow = cur.execute(
				'SELECT * FROM users WHERE id = %s', (res['user_id'],)
			).fetchone()

			if urow is None:
				raise WebError('invalid authentication token', 401)

			return User(**urow)


def get_user_from_email(email: str, password: str) -> User:
	"""Verifies if there's such a user with the email and matching passowrds"""
	with db.get_connection().cursor(row_factory=dict_row) as cur:
		row = cur.execute('SELECT * FROM users WHERE email = %s', (email,)).fetchone()

		# Handle the case where the user does not exist
		if row is None:
			raise WebError('User not found', status_code=404)

		# print("row", row)
		if not bcrypt.checkpw(password.encode(), row['hashed_password'].encode()):
			raise WebError('password incorrect', status_code=401)

		return User(**row)


def reset_password(user: User, new_password: str):
	"""Updates the password of the user object"""
	with db.get_connection().cursor() as cur:
		new_password_hashed = bcrypt.hashpw(
			new_password.encode(), bcrypt.gensalt()
		).decode()

		cur.execute(
			'UPDATE users SET hashed_password = %s WHERE id = %s',
			(
				new_password_hashed,
				user.id,
			),
		)
