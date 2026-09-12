"""Add version_id and job_posting_id to job_applications

Revision ID: 0003_application_links
Revises: 0002_master_profile_and_evidence
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_application_links"
down_revision = "0002_master_profile_and_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_applications", sa.Column("job_posting_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True))
    op.add_column("job_applications", sa.Column("version_id", sa.Integer(), sa.ForeignKey("application_versions.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("job_applications", "version_id")
    op.drop_column("job_applications", "job_posting_id")
