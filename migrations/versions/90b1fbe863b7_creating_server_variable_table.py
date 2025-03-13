"""creating server variable table

Revision ID: 90b1fbe863b7
Revises: db77872add9f
Create Date: 2025-03-13 12:25:28.654822

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90b1fbe863b7'
down_revision = 'db77872add9f'
branch_labels = None
depends_on = None


def upgrade():
	op.execute(
		"""
    	CREATE TABLE server_variables (
            id uuid PRIMARY KEY,
            key varchar(128) NOT NULL,
            description text,
            value_type varchar(42) NOT NULL,
            value_data bytea default NULL,
            value_hash varchar(512) default NULL,
            created_at timestamp with time zone default now(),
            updated_at timestamp with time zone default now()
        );"""
	)

	op.execute("""CREATE UNIQUE INDEX unique_server_key ON server_variables (key);""")

	op.execute(
		"""CREATE INDEX server_value_hash ON server_variables USING hash (value_type);"""
	)


def downgrade():
	op.execute('DROP TABLE server_variables;')
	op.execute('DROP INDEX unique_server_key;')
	op.execute('DROP INDEX server_value_hash;')
