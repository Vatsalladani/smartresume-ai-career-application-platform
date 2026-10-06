"""Subscription Pause and Retention

Revision ID: 0009_sub_retention
Revises: 0008_global_career_workspace
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_sub_retention"
down_revision = "0008_global_career_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("is_paused", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("subscriptions", sa.Column("paused_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("paused_until", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("pause_duration_months", sa.Integer(), server_default="0", nullable=False))
    op.add_column("subscriptions", sa.Column("cancellation_feedback", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("subscriptions", "cancellation_feedback")
    op.drop_column("subscriptions", "pause_duration_months")
    op.drop_column("subscriptions", "paused_until")
    op.drop_column("subscriptions", "paused_at")
    op.drop_column("subscriptions", "is_paused")
