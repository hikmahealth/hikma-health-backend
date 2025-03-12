"""Add external ids to patients, and add adopt EAV model for patient attributes

Revision ID: 602ce80e2a7b
Revises: 657ba64ed784
Create Date: 2024-05-22 23:57:19.293873

"""

from alembic import op
import sqlalchemy as sa
import datetime


# revision identifiers, used by Alembic.
revision = '602ce80e2a7b'
down_revision = '657ba64ed784'
branch_labels = None
depends_on = None


def upgrade():
	# Add new columns to the patients table
	op.add_column('patients', sa.Column('government_id', sa.String(100), nullable=True))
	op.add_column(
		'patients', sa.Column('external_patient_id', sa.String(100), nullable=True)
	)

	# Create patient_additional_attributes table
	op.create_table(
		'patient_additional_attributes',
		sa.Column('id', sa.UUID, nullable=False),
		sa.Column('patient_id', sa.String, nullable=False),  # migrated to UUIDs
		sa.Column('attribute_id', sa.String, nullable=False),
		sa.Column('attribute', sa.String, nullable=False, default=''),
		sa.Column('number_value', sa.Float, nullable=True),
		sa.Column('string_value', sa.String, nullable=True),
		sa.Column('date_value', sa.TIMESTAMP(True), nullable=True),
		sa.Column('boolean_value', sa.Boolean, nullable=True),
		sa.Column(
			'metadata', sa.JSON, nullable=False, server_default=sa.text("'{}'::json")
		),
		sa.Column('is_deleted', sa.Boolean, nullable=False, default=False),
		sa.Column(
			'created_at',
			sa.TIMESTAMP(True),
			nullable=False,
			default=datetime.datetime.utcnow,
		),
		sa.Column(
			'updated_at',
			sa.TIMESTAMP(True),
			nullable=False,
			default=datetime.datetime.utcnow,
		),
		sa.Column(
			'last_modified',
			sa.TIMESTAMP(True),
			nullable=False,
			default=datetime.datetime.utcnow,
		),
		sa.Column(
			'server_created_at',
			sa.TIMESTAMP(True),
			nullable=False,
			default=datetime.datetime.utcnow,
		),
		sa.Column('deleted_at', sa.TIMESTAMP(True), nullable=True),
		# composite index allows for uniquely identifying these two columns. there shouldn't be two of these
		sa.PrimaryKeyConstraint('patient_id', 'attribute_id'),
		sa.Index('ix_patient_additional_attributes_patient_id', 'patient_id'),
		sa.Index('ix_patient_additional_attributes_attribute_id', 'attribute_id'),
	)


def downgrade():
	op.drop_column('patients', 'government_id')
	op.drop_column('patients', 'external_patient_id')

	# Drop patient_additional_attributes table
	op.drop_table('patient_additional_attributes')
