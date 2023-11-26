"""patient additional data

Revision ID: f528ab1cd8ea
Revises: 7f49e3d0c1a2
Create Date: 2023-11-02 00:28:14.461785

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f528ab1cd8ea'
down_revision = '7f49e3d0c1a2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('patients', sa.Column('additional_data', sa.JSON(), nullable=True))
    op.add_column('patients', sa.Column('metadata', sa.JSON(), nullable=True))

    op.execute("UPDATE patients SET additional_data = '{}'")
    op.execute("UPDATE patients SET metadata = '{}'")

    op.alter_column('patients', 'additional_data', nullable=False, server_default='{}')
    op.alter_column('patients', 'metadata', nullable=False, server_default='{}')


def downgrade():
    op.drop_column("patients", "additional_data")
    op.drop_column("patients", "metadata")
