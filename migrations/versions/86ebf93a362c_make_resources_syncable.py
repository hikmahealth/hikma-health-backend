"""make resources syncable

Revision ID: 86ebf93a362c
Revises: fbcd98789c00
Create Date: 2025-04-01 00:22:55.705506

"""

from alembic import op
import sqlalchemy as sa
from importlib import resources


# revision identifiers, used by Alembic.
revision = '86ebf93a362c'
down_revision = 'fbcd98789c00'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE resources
        ADD COLUMN is_deleted boolean default false;
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE resources
        DROP COLUMN is_deleted;
        """
    )
