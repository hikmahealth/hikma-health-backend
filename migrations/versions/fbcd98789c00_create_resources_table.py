"""create resources table

Revision ID: fbcd98789c00
Revises: 90b1fbe863b7
Create Date: 2025-03-20 14:35:57.492606

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbcd98789c00'
down_revision = '90b1fbe863b7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE resources (
            id uuid PRIMARY KEY,
            description TEXT,
            store varchar(42) NOT NULL,
            store_version varchar(42) NOT NULL,
            uri TEXT NOT NULL,
            hash varchar(512) default NULL,
            created_at timestamp with time zone default now(),
            updated_at timestamp with time zone default now()
        );
        """
    )

    op.execute('CREATE UNIQUE INDEX unique_resource_ix ON resources (store, uri);')
    op.execute('CREATE INDEX store_type_ix ON resources (store) ')


def downgrade():
    op.execute('DROP INDEX store_type_ix;')
    op.execute('DROP INDEX unique_resource_ix;')
    op.execute('DROP TABLE resources;')
