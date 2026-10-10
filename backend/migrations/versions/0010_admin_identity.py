"""Dedicated Administrator Identity and Invitations

Revision ID: 0010_admin_identity
Revises: 0009_sub_retention
Create Date: 2026-10-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_admin_identity"
down_revision = "0009_sub_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create admin_accounts table
    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("username", sa.String(100), unique=True, nullable=True, index=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="ADMIN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 2. Create admin_invitations table
    op.create_table(
        "admin_invitations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("token_hash", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("role", sa.String(30), nullable=False, server_default="ADMIN"),
        sa.Column("invited_by_admin_id", sa.Integer(), sa.ForeignKey("admin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("consumed_by_admin_id", sa.Integer(), sa.ForeignKey("admin_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("admin_invitations")
    op.drop_table("admin_accounts")
