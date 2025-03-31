"""include healthcare provider segmentation

Revision ID: 18edc29dd7fd
Revises: 86ebf93a362c
Create Date: 2025-04-01 00:35:00.929848

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '18edc29dd7fd'
down_revision = '86ebf93a362c'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE clinics
        ADD COLUMN attributes text[] NOT NULL default ARRAY[]::text[],
        ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}',
        ADD COLUMN address text default NULL;
        """
    )

    op.execute(
        """CREATE INDEX attributes_hash_ix ON clinics USING hash (attributes);"""
    )


def downgrade():
    op.execute('DROP INDEX attributes_hash_ix;')
    op.execute(
        """
        ALTER TABLE clinics
        DROP COLUMN attributes,
        DROP COLUMN metadata,
        DROP COLUMN address;
        """
    )
