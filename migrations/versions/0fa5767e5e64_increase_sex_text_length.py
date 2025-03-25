"""increase sex text length

Revision ID: 0fa5767e5e64
Revises: 19c8d4aed7fa
Create Date: 2024-08-21 11:12:54.868256

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0fa5767e5e64'
down_revision = '19c8d4aed7fa'
branch_labels = None
depends_on = None


def upgrade():
	op.alter_column(
		'patients',
		'sex',
		existing_type=sa.VARCHAR(length=8),
		type_=sa.VARCHAR(length=24),
		existing_nullable=True,
	)


def downgrade():
	op.alter_column(
		'patients',
		'sex',
		existing_type=sa.VARCHAR(length=24),
		type_=sa.VARCHAR(length=8),
		existing_nullable=True,
	)
