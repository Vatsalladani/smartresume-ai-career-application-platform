from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reset_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("ATSAnalysis", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    @property
    def plan_name(self) -> str:
        sub = self.subscription
        if not sub:
            return "FREE"
        if sub.status == "ACTIVE":
            now = datetime.utcnow()
            if sub.plan_name in ("PRO_MONTHLY", "PRO_ANNUAL", "EXECUTIVE"):
                if sub.expires_at and sub.expires_at < now:
                    return "FREE"
                return sub.plan_name
            if sub.plan_name == "PRO_TRIAL" or sub.is_trial:
                if sub.trial_expires_at and sub.trial_expires_at < now:
                    return "FREE"
                return "PRO_TRIAL"
            return sub.plan_name or "FREE"
        return "FREE"

    @property
    def subscription_status(self) -> str:
        sub = self.subscription
        if not sub:
            return "ACTIVE"
        now = datetime.utcnow()
        if sub.status == "ACTIVE":
            if (sub.expires_at and sub.expires_at < now) or (sub.is_trial and sub.trial_expires_at and sub.trial_expires_at < now):
                return "EXPIRED"
            return "ACTIVE"
        return sub.status
