"""Add enhanced fields to job_applications: location, work_arrangement, source, applied_date, deadline_date, salary_range, contact_name, contact_email, contact_phone, is_archived

Revision ID: 0013_app_tracker_fields
Revises: 0012_interview_simulator_v2
Create Date: 2026-10-16 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0013_app_tracker_fields"
down_revision = "0012_interview_simulator_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_applications") as batch_op:
        batch_op.add_column(sa.Column("location", sa.String(length=150), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("work_arrangement", sa.String(length=50), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("source", sa.String(length=100), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("applied_date", sa.String(length=50), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("deadline_date", sa.String(length=50), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("salary_range", sa.String(length=100), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("contact_name", sa.String(length=150), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("contact_email", sa.String(length=150), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("contact_phone", sa.String(length=50), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    with op.batch_alter_table("job_applications") as batch_op:
        batch_op.drop_column("is_archived")
        batch_op.drop_column("contact_phone")
        batch_op.drop_column("contact_email")
        batch_op.drop_column("contact_name")
        batch_op.drop_column("salary_range")
        batch_op.drop_column("deadline_date")
        batch_op.drop_column("applied_date")
        batch_op.drop_column("source")
        batch_op.drop_column("work_arrangement")
        batch_op.drop_column("location")
