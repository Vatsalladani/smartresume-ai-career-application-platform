"""Global career workspace, international resume rules, and post-hire career status

Revision ID: 0008_global_career_workspace
Revises: 0007_multi_resume_ctx
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_global_career_workspace"
down_revision = "0007_multi_resume_ctx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Resumes table extensions for international market rules & document purpose
    op.add_column("resumes", sa.Column("target_market", sa.String(50), server_default="Global", nullable=False))
    op.add_column("resumes", sa.Column("document_purpose", sa.String(50), server_default="Professional Resume", nullable=False))
    op.add_column("resumes", sa.Column("ats_mode", sa.String(30), server_default="ATS-Safe", nullable=False))

    # 2. Profiles table extensions for career status (post-hire retention) and default market
    op.add_column("profiles", sa.Column("career_status", sa.String(50), server_default="Job Searching", nullable=False))
    op.add_column("profiles", sa.Column("target_market", sa.String(50), server_default="Global", nullable=False))


def downgrade() -> None:
    op.drop_column("profiles", "target_market")
    op.drop_column("profiles", "career_status")

    op.drop_column("resumes", "ats_mode")
    op.drop_column("resumes", "document_purpose")
    op.drop_column("resumes", "target_market")
