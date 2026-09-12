from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False, default="My Resume")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ats_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    public_share_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan", order_by="ResumeVersion.version_number")
    analyses = relationship("ATSAnalysis", back_populates="resume", cascade="all, delete-orphan")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analysis_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    changelog: Mapped[str] = mapped_column(String(255), nullable=False, default="Saved version")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="versions")


class ATSAnalysis(Base):
    __tablename__ = "ats_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    original_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    predicted_ats_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    keyword_report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    suggestions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enhanced_content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
