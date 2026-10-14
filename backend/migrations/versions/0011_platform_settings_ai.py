"""Canonical Platform Settings and AI Operational Logs

Revision ID: 0011_platform_settings_ai
Revises: 0010_admin_identity
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_platform_settings_ai"
down_revision = "0010_admin_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create platform_settings table if not exists
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(30), nullable=False, server_default="string"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 2. Create ai_operation_logs table
    op.create_table(
        "ai_operation_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("feature_name", sa.String(80), nullable=False, index=True),
        sa.Column("ai_provider", sa.String(50), nullable=False, index=True),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("ai_operation_logs")
    op.drop_table("platform_settings")
