"""create patient registration forms table

Revision ID: 7f49e3d0c1a2
Revises: 657ba64ed784
Create Date: 2023-11-01 15:48:02.513266

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f49e3d0c1a2'
down_revision = '657ba64ed784'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
       CREATE TABLE patient_registration_forms (
            id uuid PRIMARY KEY,
            name text NOT NULL DEFAULT '',
            fields JSONB NOT NULL DEFAULT '[]',
            metadata JSONB NOT NULL DEFAULT '{}',
            is_deleted boolean default false,
            created_at timestamp with time zone default now(),
            updated_at timestamp with time zone default now(),
            last_modified timestamp with time zone default now(),
            server_created_at timestamp with time zone default now(),
            deleted_at timestamp with time zone default null
        ) 
        """
    )


def downgrade():
    op.execute("DROP TABLE patient_registration_forms;")
