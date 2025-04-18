"""Create initial user

Revision ID: 657ba64ed784
Revises: 47dc360e825a
Create Date: 2019-11-25 18:33:30.688004

"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime
import uuid


# revision identifiers, used by Alembic.
revision = '657ba64ed784'
down_revision = '47dc360e825a'
branch_labels = None
depends_on = None


def upgrade():
	# define the clinic_id
	clinic_id = str(uuid.uuid4())
	op.execute(
		f"""
        INSERT INTO clinics (id, name) VALUES ('{clinic_id}', 'Hikma Clinic')
        """
	)

	op.execute(
		f"""
    INSERT INTO users (id, clinic_id, name, role, email, hashed_password, instance_url, created_at, updated_at, is_deleted)
    VALUES ('{str(uuid.uuid4())}', '{clinic_id}', 'Hikma Admin', 'super_admin', 'admin@hikmahealth.org',
            '$2b$14$PPY9X2ZxFG93IU9CK4FUtOJW0d11zjHuODO6oJM5UNn59aXjp5h..', '{None}', '{datetime.now().isoformat()}', '{datetime.now().isoformat()}', '{False}')
    """
	)


def downgrade():
	op.execute("DELETE FROM users WHERE email = 'admin@hikmahealth.org';")
