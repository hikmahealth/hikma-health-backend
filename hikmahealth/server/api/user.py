from __future__ import annotations
import bcrypt

from hikmahealth.server.client import db

from hikmahealth.server.api.user import User
from hikmahealth.server.client import db
from hikmahealth.server.utils.errors import WebError

import bcrypt
from psycopg.rows import dict_row

class User(object):
    # def __init__(self, id, email):
    def __init__(self, id, name, role, email, clinic_id):
        self.id = id
        self.name = name
        self.role = role
        self.email = email
        self.clinic_id = clinic_id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "email": self.email,
            "clinic_id": self.clinic_id,
        }


def authenticate_with_email(email: str, password: str) -> User:
        """Verifies if there's such a user with the email and matching passowrds"""
        with db.get_connection().cursor(row_factory=dict_row) as cur:
            cur.execute(
                'SELECT * FROM users WHERE email = %s',
                (email,)
            )

            row = cur.fetchone()
            if not bcrypt.checkpw(password.encode(), row['hashed_password']):
                raise WebError("password incorrect", status_code=401)
            
            return User(**row)


def reset_password(user: User, new_password: str):
    """Updates the password of the user object"""
    with db.get_connection().cursor() as cur:
            new_password_hashed = bcrypt.hashpw(
                new_password.encode(), bcrypt.gensalt()).decode()
            
            cur.execute('UPDATE users SET hashed_password = %s WHERE id = %s',
                        (new_password_hashed, user.id,))
            
