from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_month: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    fit_analyses_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tailored_versions_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exports_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_credits_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "period_month", name="uq_user_usage_period"),
    )
