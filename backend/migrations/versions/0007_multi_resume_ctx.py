"""Multi-resume drafts and interview target context

Revision ID: 0007_multi_resume_ctx
Revises: 0006_sub_lifecycle
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_multi_resume_ctx"
down_revision = "0006_sub_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Resumes table extensions for multi-resume workspace
    op.add_column("resumes", sa.Column("status", sa.String(30), server_default="Draft", nullable=False))
    op.add_column("resumes", sa.Column("target_role", sa.String(150), nullable=True))
    op.add_column("resumes", sa.Column("target_company", sa.String(150), nullable=True))
    op.add_column("resumes", sa.Column("target_location", sa.String(150), nullable=True))
    op.add_column("resumes", sa.Column("target_job_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_resumes_job_postings",
        "resumes",
        "job_postings",
        ["target_job_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.add_column("resumes", sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False))

    # 2. Interview sessions extensions to link selected resume and job description snapshot
    op.add_column("interview_sessions", sa.Column("resume_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_interview_sessions_resumes",
        "interview_sessions",
        "resumes",
        ["resume_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.add_column("interview_sessions", sa.Column("job_description_snapshot", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("interview_sessions", "job_description_snapshot")
    op.drop_constraint("fk_interview_sessions_resumes", "interview_sessions", type_="foreignkey")
    op.drop_column("interview_sessions", "resume_id")

    op.drop_column("resumes", "is_archived")
    op.drop_constraint("fk_resumes_job_postings", "resumes", type_="foreignkey")
    op.drop_column("resumes", "target_job_id")
    op.drop_column("resumes", "target_location")
    op.drop_column("resumes", "target_company")
    op.drop_column("resumes", "target_role")
    op.drop_column("resumes", "status")
