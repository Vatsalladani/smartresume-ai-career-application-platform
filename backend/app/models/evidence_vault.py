from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="PROJECT")  # PROJECT, EXPERIENCE, CERTIFICATION, EDUCATION, ACHIEVEMENT, METRIC, SKILL
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    date: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    context: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    experience_id: Mapped[int | None] = mapped_column(ForeignKey("experiences.id", ondelete="SET NULL"), nullable=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")  # manual, resume_import, smartbuild, experience, project
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="VERIFIED")  # VERIFIED, SUPPORTED, PARTIALLY_SUPPORTED, PROFILE_ONLY, UNSUPPORTED, UNCLEAR
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="evidence_items")
    project = relationship("Project")
    experience = relationship("Experience")
    skill = relationship("Skill")
