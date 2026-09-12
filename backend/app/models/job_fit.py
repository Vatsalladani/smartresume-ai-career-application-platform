from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    company: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    job_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_domain: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    career_level: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    parsed_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_signals: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    requirements = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan", order_by="JobRequirement.order_index")
    evidence_links = relationship("EvidenceLink", back_populates="job", cascade="all, delete-orphan")
    versions = relationship("ApplicationVersion", back_populates="job", cascade="all, delete-orphan", order_by="ApplicationVersion.version_number")


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="MUST_HAVE")  # MUST_HAVE or PREFERRED
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="skill")  # skill, experience, education, tool, domain
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    job = relationship("JobPosting", back_populates="requirements")
    evidence_links = relationship("EvidenceLink", back_populates="requirement", cascade="all, delete-orphan")


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("job_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNCLEAR")  # STRONG, PARTIAL, MISSING, UNCLEAR
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, default="experience")  # experience, project, skill, education, certification
    evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_quote: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gap_explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    user_actionable_hint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False, default="")
    learning_suggestion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggested_project: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    job = relationship("JobPosting", back_populates="evidence_links")
    requirement = relationship("JobRequirement", back_populates="evidence_links")


class ApplicationVersion(Base):
    __tablename__ = "application_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_name: Mapped[str] = mapped_column(String(50), nullable=False, default="classic_ats")
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    diff_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ats_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    changelog: Mapped[str] = mapped_column(String(255), nullable=False, default="Initial tailoring")
    readiness_report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    consistency_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    application_pack: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("job_id", "version_number", name="uq_app_version_job_version"),
    )

    job = relationship("JobPosting", back_populates="versions")
    ats_checks = relationship("ATSCheck", back_populates="version", cascade="all, delete-orphan")


class ATSCheck(Base):
    __tablename__ = "ats_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("application_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    format_health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    keyword_coverage_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    application_fit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    readiness_level: Mapped[str] = mapped_column(String(30), nullable=False, default="READY")  # READY, NEEDS_EVIDENCE, FORMAT_RISK
    detailed_report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    version = relationship("ApplicationVersion", back_populates="ats_checks")
