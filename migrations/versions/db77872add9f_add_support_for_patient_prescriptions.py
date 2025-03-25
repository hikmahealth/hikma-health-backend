"""add support for patient prescriptions

Revision ID: db77872add9f
Revises: 80e8c595e01e
Create Date: 2024-09-26 16:01:59.120977

"""

from datetime import UTC, datetime
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db77872add9f'
down_revision = '80e8c595e01e'
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		'prescriptions',
		sa.Column('id', sa.UUID(), nullable=False),
		sa.Column('patient_id', sa.UUID(), nullable=False),
		sa.Column('provider_id', sa.UUID(), nullable=False),
		sa.Column(
			'filled_by', sa.UUID(), nullable=True, default=None, server_default=None
		),
		sa.Column('pickup_clinic_id', sa.UUID(), nullable=False),
		sa.Column(
			'visit_id', sa.UUID(), nullable=True, default=None, server_default=None
		),
		sa.Column('priority', sa.String(), nullable=True, server_default='normal'),
		sa.Column(
			'expiration_date',
			sa.DateTime(timezone=True),
			nullable=True,
			default=None,
			server_default=None,
		),
		sa.Column(
			'prescribed_at',
			sa.DateTime(timezone=True),
			nullable=False,
			default=datetime.now(UTC),
			server_default=sa.text('CURRENT_TIMESTAMP'),
		),
		sa.Column(
			'filled_at',
			sa.DateTime(timezone=True),
			nullable=True,
			default=None,
			server_default=None,
		),
		sa.Column(
			'status',
			sa.String(),
			nullable=False,
			default='pending',
			server_default='pending',
		),
		sa.Column(
			'items', sa.JSON(), nullable=False, default='[]', server_default='[]'
		),
		sa.Column('notes', sa.String(), nullable=False, server_default=''),
		sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
		sa.Column(
			'is_deleted',
			sa.Boolean(),
			nullable=False,
			default=False,
			server_default='false',
		),
		sa.Column(
			'created_at',
			sa.DateTime(timezone=True),
			nullable=False,
			default=datetime.now(UTC),
			server_default=sa.text('CURRENT_TIMESTAMP'),
		),
		sa.Column(
			'updated_at',
			sa.DateTime(timezone=True),
			nullable=False,
			default=datetime.now(UTC),
			server_default=sa.text('CURRENT_TIMESTAMP'),
		),
		sa.Column(
			'deleted_at',
			sa.DateTime(timezone=True),
			nullable=True,
			default=None,
			server_default=None,
		),
		sa.Column(
			'last_modified',
			sa.DateTime(timezone=True),
			nullable=False,
			default=datetime.now(UTC),
			server_default=sa.text('CURRENT_TIMESTAMP'),
			onupdate=sa.text('CURRENT_TIMESTAMP'),
		),
		sa.Column(
			'server_created_at',
			sa.DateTime(timezone=True),
			nullable=False,
			default=datetime.now(UTC),
			server_default=sa.text('CURRENT_TIMESTAMP'),
		),
	)

	# Create primary key
	op.create_primary_key('pk_prescriptions', 'prescriptions', ['id'])

	# Create foreign keys
	op.create_foreign_key(
		'fk_prescriptions_patient', 'prescriptions', 'patients', ['patient_id'], ['id']
	)
	op.create_foreign_key(
		'fk_prescriptions_provider', 'prescriptions', 'users', ['provider_id'], ['id']
	)
	op.create_foreign_key(
		'fk_prescriptions_pickup_clinic',
		'prescriptions',
		'clinics',
		['pickup_clinic_id'],
		['id'],
	)

	# Create indexes
	op.create_index(
		'ix_prescriptions_patient_id', 'prescriptions', ['patient_id'], unique=False
	)
	op.create_index(
		'ix_prescriptions_pickup_clinic_id',
		'prescriptions',
		['pickup_clinic_id'],
		unique=False,
	)


def downgrade():
	# Drop indexes
	op.drop_index('ix_prescriptions_pickup_clinic_id', table_name='prescriptions')
	op.drop_index('ix_prescriptions_patient_id', table_name='prescriptions')

	# Drop foreign keys
	op.drop_constraint(
		'fk_prescriptions_pickup_clinic', 'prescriptions', type_='foreignkey'
	)
	op.drop_constraint('fk_prescriptions_patient', 'prescriptions', type_='foreignkey')
	op.drop_constraint('fk_prescriptions_provider', 'prescriptions', type_='foreignkey')

	# Drop primary key
	op.drop_constraint('pk_prescriptions', 'prescriptions', type_='primary')

	# Drop table
	op.drop_table('prescriptions')
