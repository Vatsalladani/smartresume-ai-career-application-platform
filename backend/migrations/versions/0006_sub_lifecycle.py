"""Subscription Lifecycle and AutoPay Columns

Revision ID: 0006_sub_lifecycle
Revises: 0005_career_and_application_os
Create Date: 2026-09-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_sub_lifecycle"
down_revision = "0005_career_and_application_os"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("payment_method_type", sa.String(30), server_default="none", nullable=False))
    op.add_column("subscriptions", sa.Column("payment_method_detail", sa.String(100), nullable=True))
    op.add_column("subscriptions", sa.Column("upi_app", sa.String(50), nullable=True))
    op.add_column("subscriptions", sa.Column("cancellation_scheduled", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("subscriptions", sa.Column("cancellation_reason", sa.String(255), nullable=True))
    op.add_column("subscriptions", sa.Column("last_payment_error", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("subscriptions", "last_payment_error")
    op.drop_column("subscriptions", "cancellation_reason")
    op.drop_column("subscriptions", "cancellation_scheduled")
    op.drop_column("subscriptions", "upi_app")
    op.drop_column("subscriptions", "payment_method_detail")
    op.drop_column("subscriptions", "payment_method_type")
