"""Dedicated Admin Account and Invitation Models for SmartResume.ai.

Separates Administrator identities completely from regular user accounts.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AdminAccount(Base):
    __tablename__ = "admin_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="ADMIN")  # "OWNER_ADMIN", "ADMIN", "READONLY_ADMIN"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    invitations_sent = relationship(
        "AdminInvitation",
        foreign_keys="[AdminInvitation.invited_by_admin_id]",
        back_populates="inviter",
        cascade="all, delete-orphan",
    )
    invitation_consumed = relationship(
        "AdminInvitation",
        foreign_keys="[AdminInvitation.consumed_by_admin_id]",
        back_populates="consumed_by",
    )


class AdminInvitation(Base):
    __tablename__ = "admin_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="ADMIN")
    invited_by_admin_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("admin_accounts.id", ondelete="CASCADE"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consumed_by_admin_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("admin_accounts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    inviter = relationship("AdminAccount", foreign_keys=[invited_by_admin_id], back_populates="invitations_sent")
    consumed_by = relationship("AdminAccount", foreign_keys=[consumed_by_admin_id], back_populates="invitation_consumed")
