from hikmahealth.server.client import db

from psycopg.rows import dict_row, class_row


class SimpleCRUD:
	"""Utility class containing simple operations to make fetches on the application"""

	@property
	@classmethod
	def TABLE_NAME(self) -> str:
		"""This refers to the name of the able associated with
		the entity"""
		raise NotImplementedError(
			f'require {__class__.__name__}.TABLE_NAME to be defined'
		)

	@classmethod
	def from_id(cls, id: str):
		with db.get_connection().cursor(row_factory=class_row(cls)) as cur:
			node = cur.execute(
				"""
                SELECT * FROM {} WHERE is_deleted = FALSE AND id = %s;
                """.format(cls.TABLE_NAME),
				[id],
			).fetchone()

		return node

	@classmethod
	def get_all(cls):
		with db.get_connection().cursor(row_factory=class_row(cls)) as cur:
			node = cur.execute(
				"""
                SELECT * FROM {} WHERE is_deleted = FALSE;
                """.format(cls.TABLE_NAME),
			).fetchall()

		return node

	@classmethod
	def get_many(cls, limit: int):
		with db.get_connection().cursor(row_factory=class_row(cls)) as cur:
			node = cur.execute(
				"""
                SELECT * FROM {} WHERE is_deleted = FALSE;
                """.format(cls.TABLE_NAME),
			).fetchmany(limit)

		return node
