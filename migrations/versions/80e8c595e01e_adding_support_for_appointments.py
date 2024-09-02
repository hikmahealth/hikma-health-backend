"""Adding support for Appointments

Revision ID: 80e8c595e01e
Revises: 0fa5767e5e64
Create Date: 2024-09-01 16:58:25.334801

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, UTC

# revision identifiers, used by Alembic.
revision = '80e8c595e01e'
down_revision = '0fa5767e5e64'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "appointments",
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=True),
        sa.Column('clinic_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('current_visit_id', sa.UUID(), nullable=False),
        sa.Column('fulfilled_visit_id', sa.UUID(), nullable=True),

        sa.Column('timestamp', sa.TIMESTAMP(True), nullable=False),

        # Duration in minutes, defaults to 60 minutes
        sa.Column('duration', sa.SmallInteger(), nullable=False, default=60),

        sa.Column('reason', sa.String(), nullable=False, default=""),
        sa.Column('notes', sa.String(), nullable=False, default=""),

        # Status can be pending, confirmed, cancelled, or completed
        sa.Column('status', sa.String(), nullable=False, default="pending"),

        sa.Column('metadata', sa.JSON(), nullable=False,
                  server_default=sa.text("'{}'::json")),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.TIMESTAMP(True),
                  nullable=False, default=datetime.now(UTC)),
        sa.Column('updated_at', sa.TIMESTAMP(True),
                  nullable=False, default=datetime.now(UTC)),
        sa.Column('last_modified', sa.TIMESTAMP(True),
                  nullable=False, default=datetime.now(UTC)),
        sa.Column('server_created_at', sa.TIMESTAMP(True),
                  nullable=False, default=datetime.now(UTC)),
        sa.Column('deleted_at', sa.TIMESTAMP(True), nullable=True),
    )

    op.create_index("ix_timestamp", "appointments", ["timestamp"])

    op.create_primary_key("appointments_pkey", "appointments", ["id"])

    op.create_foreign_key("fk_appointment_clinic",
                          "appointments", "clinics", ["clinic_id"], ["id"])
    op.create_foreign_key("fk_appointment_patient",
                          "appointments", "patients", ["patient_id"], ["id"])
    op.create_foreign_key("fk_appointment_user",
                          "appointments", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_appointment_provider",
                          "appointments", "users", ["provider_id"], ["id"])
    op.create_foreign_key("fk_appointment_current_visit",
                          "appointments", "visits", ["current_visit_id"], ["id"])
    op.create_foreign_key("fk_appointment_fulfilled_visit",
                          "appointments", "visits", ["fulfilled_visit_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_appointment_provider", table_name="appointments")
    op.drop_constraint("fk_appointment_clinic", table_name="appointments")
    op.drop_constraint("fk_appointment_patient", table_name="appointments")
    op.drop_constraint("fk_appointment_user", table_name="appointments")
    op.drop_constraint("fk_appointment_current_visit",
                       table_name="appointments")
    op.drop_constraint("fk_appointment_fulfilled_visit",
                       table_name="appointments")

    op.drop_index("ix_timestamp", table_name="appointments")

    op.drop_constraint("appointments_pkey", table_name="appointments")

    op.drop_table("appointments")
