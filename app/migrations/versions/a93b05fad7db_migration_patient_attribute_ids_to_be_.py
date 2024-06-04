"""migration patient attribute ids to be UUIDs

Revision ID: a93b05fad7db
Revises: 602ce80e2a7b
Create Date: 2024-06-03 20:39:09.023041

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision = 'a93b05fad7db'
down_revision = '602ce80e2a7b'
branch_labels = None
depends_on = None


def upgrade():
     # Add a new UUID column
    op.add_column('patient_additional_attributes', sa.Column('patient_uuid_column', postgresql.UUID(), nullable=True))

    # Convert existing string values to UUID
    op.execute('''
        UPDATE patient_additional_attributes
        SET patient_uuid_column = patient_id::UUID
    ''')

    # Drop the old string column
    op.drop_column('patient_additional_attributes', 'patient_id')

    # Rename the new UUID column to the original column name
    op.alter_column('patient_additional_attributes', 'patient_uuid_column', new_column_name='patient_id')



def downgrade():
    # Add the old string column back
    op.add_column('patient_additional_attributes', sa.Column('patient_id', sa.String(), nullable=True))

    # Convert UUID values back to string
    op.execute('''
        UPDATE patient_additional_attributes
        SET patient_id = patient_uuid_column::TEXT
    ''')

    # Drop the new UUID column
    op.drop_column('patient_additional_attributes', 'patient_uuid_column')
