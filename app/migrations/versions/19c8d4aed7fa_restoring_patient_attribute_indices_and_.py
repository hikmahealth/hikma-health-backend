"""restoring patient attribute indices and primary keys

Revision ID: 19c8d4aed7fa
Revises: a93b05fad7db
Create Date: 2024-07-11 23:08:19.705851

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '19c8d4aed7fa'
down_revision = 'a93b05fad7db'
branch_labels = None
depends_on = None

def upgrade():
    # Make patient_id non-nullable
    op.alter_column('patient_additional_attributes', 'patient_id',
               existing_type=postgresql.UUID(),
               nullable=False)
    
    # Create the primary key constraint
    op.create_primary_key('patient_additional_attributes_pkey', 'patient_additional_attributes', ['patient_id', 'attribute_id'])
    
    # Create an index on patient_id
    op.create_index('ix_patient_additional_attributes_patient_id', 'patient_additional_attributes', ['patient_id'])

def downgrade():
    # Drop the primary key constraint
    op.drop_constraint('patient_additional_attributes_pkey', 'patient_additional_attributes', type_='primary')
    
    # Drop the index
    op.drop_index('ix_patient_additional_attributes_patient_id', table_name='patient_additional_attributes')
    
    # Make patient_id nullable (reverting to the state after the previous migration)
    op.alter_column('patient_additional_attributes', 'patient_id',
               existing_type=postgresql.UUID(),
               nullable=True)
