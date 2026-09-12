"""Career OS and Application OS: Evidence Vault, Interview Copilot, Notifications, and Pack Schema

Revision ID: 0005_career_and_application_os
Revises: 0004_product_intelligence_v2
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_career_and_application_os"
down_revision = "0004_product_intelligence_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Evidence items table
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False, server_default="PROJECT"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("date", sa.String(50), nullable=False, server_default=""),
        sa.Column("context", sa.String(200), nullable=False, server_default=""),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("experience_id", sa.Integer(), sa.ForeignKey("experiences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(100), nullable=False, server_default="manual"),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="VERIFIED"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # 2. Interview sessions table
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("application_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_role", sa.String(150), nullable=False, server_default=""),
        sa.Column("target_company", sa.String(150), nullable=False, server_default=""),
        sa.Column("session_mode", sa.String(20), nullable=False, server_default="TEXT"),
        sa.Column("status", sa.String(30), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # 3. Interview messages table
    op.create_table(
        "interview_messages",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sender", sa.String(10), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.String(255), nullable=True),
        sa.Column("evaluation_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # 4. Interview evaluations table
    op.create_table(
        "interview_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("strong_areas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("needs_practice", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("technical_gaps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("communication_improvements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("resume_claims_to_defend", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("suggested_questions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("readiness_level", sa.String(30), nullable=False, server_default="NEEDS_PRACTICE"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # 5. Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="INFO"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("action_url", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # 6. Alter job_applications
    op.add_column("job_applications", sa.Column("cover_letter_text", sa.Text(), nullable=False, server_default=""))
    op.add_column("job_applications", sa.Column("email_draft_json", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("job_applications", sa.Column("application_answers_json", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("job_applications", sa.Column("follow_up_date", sa.String(50), nullable=False, server_default=""))
    op.add_column("job_applications", sa.Column("interview_date", sa.String(50), nullable=False, server_default=""))
    op.add_column("job_applications", sa.Column("interview_notes", sa.Text(), nullable=False, server_default=""))
    op.add_column("job_applications", sa.Column("outcome", sa.String(50), nullable=False, server_default=""))

    # 7. Alter subscriptions
    op.add_column("subscriptions", sa.Column("trial_starts_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("trial_expires_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("is_trial", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # 8. Alter job_postings
    op.add_column("job_postings", sa.Column("risk_signals", sa.JSON(), nullable=False, server_default="{}"))

    # 9. Alter application_versions
    op.add_column("application_versions", sa.Column("application_pack", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("application_versions", "application_pack")
    op.drop_column("job_postings", "risk_signals")
    op.drop_column("subscriptions", "is_trial")
    op.drop_column("subscriptions", "trial_expires_at")
    op.drop_column("subscriptions", "trial_starts_at")
    op.drop_column("job_applications", "outcome")
    op.drop_column("job_applications", "interview_notes")
    op.drop_column("job_applications", "interview_date")
    op.drop_column("job_applications", "follow_up_date")
    op.drop_column("job_applications", "application_answers_json")
    op.drop_column("job_applications", "email_draft_json")
    op.drop_column("job_applications", "cover_letter_text")
    op.drop_table("notifications")
    op.drop_table("interview_evaluations")
    op.drop_table("interview_messages")
    op.drop_table("interview_sessions")
    op.drop_table("evidence_items")
