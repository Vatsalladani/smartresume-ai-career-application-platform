"""Add 60-minute interview simulator lifecycle, timer, phases, strict focus and multi-dimensional scoring

Revision ID: 0012_interview_simulator_v2
Revises: 0011_platform_settings_ai
Create Date: 2026-10-14 15:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0012_interview_simulator_v2"
down_revision = "0011_platform_settings_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add fields to interview_sessions
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.add_column(sa.Column("career_level", sa.String(length=50), nullable=False, server_default="Intermediate"))
        batch_op.add_column(sa.Column("difficulty", sa.String(length=50), nullable=False, server_default="Adaptive"))
        batch_op.add_column(sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("ended_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("current_phase", sa.String(length=100), nullable=False, server_default="Introduction & Communication"))
        batch_op.add_column(sa.Column("current_phase_index", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="false"))
        batch_op.add_column(sa.Column("paused_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("total_paused_seconds", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("focus_coach_enabled", sa.Boolean(), nullable=False, server_default="false"))
        batch_op.add_column(sa.Column("strict_focus_mode", sa.Boolean(), nullable=False, server_default="false"))
        batch_op.add_column(sa.Column("focus_warnings_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("focus_warning_history", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("coverage_plan", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("termination_reason", sa.String(length=255), nullable=True))

    # 2. Add fields to interview_evaluations
    with op.batch_alter_table("interview_evaluations") as batch_op:
        batch_op.add_column(sa.Column("overall_score", sa.Integer(), nullable=False, server_default="70"))
        batch_op.add_column(sa.Column("technical_score", sa.Integer(), nullable=False, server_default="70"))
        batch_op.add_column(sa.Column("problem_solving_score", sa.Integer(), nullable=False, server_default="70"))
        batch_op.add_column(sa.Column("communication_score", sa.Integer(), nullable=False, server_default="70"))
        batch_op.add_column(sa.Column("resume_knowledge_score", sa.Integer(), nullable=False, server_default="70"))
        batch_op.add_column(sa.Column("role_readiness_score", sa.Integer(), nullable=False, server_default="70"))
        batch_op.add_column(sa.Column("holding_back", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("suggested_next_practice", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("voice_delivery_metrics", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("coverage_summary", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("termination_reason", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("interview_evaluations") as batch_op:
        batch_op.drop_column("termination_reason")
        batch_op.drop_column("coverage_summary")
        batch_op.drop_column("voice_delivery_metrics")
        batch_op.drop_column("suggested_next_practice")
        batch_op.drop_column("holding_back")
        batch_op.drop_column("role_readiness_score")
        batch_op.drop_column("resume_knowledge_score")
        batch_op.drop_column("communication_score")
        batch_op.drop_column("problem_solving_score")
        batch_op.drop_column("technical_score")
        batch_op.drop_column("overall_score")

    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_column("termination_reason")
        batch_op.drop_column("coverage_plan")
        batch_op.drop_column("focus_warning_history")
        batch_op.drop_column("focus_warnings_count")
        batch_op.drop_column("strict_focus_mode")
        batch_op.drop_column("focus_coach_enabled")
        batch_op.drop_column("total_paused_seconds")
        batch_op.drop_column("paused_at")
        batch_op.drop_column("is_paused")
        batch_op.drop_column("current_phase_index")
        batch_op.drop_column("current_phase")
        batch_op.drop_column("ended_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("duration_minutes")
        batch_op.drop_column("difficulty")
        batch_op.drop_column("career_level")
