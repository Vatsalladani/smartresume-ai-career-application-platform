from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    job_posting_id: Mapped[int | None] = mapped_column(ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True)
    version_id: Mapped[int | None] = mapped_column(ForeignKey("application_versions.id", ondelete="SET NULL"), nullable=True)
    company: Mapped[str] = mapped_column(String(150), nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SAVED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(150), nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cover_letter_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email_draft_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    application_answers_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    follow_up_date: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    interview_date: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    interview_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcome: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    resume = relationship("Resume")
    job_posting = relationship("JobPosting")
    version = relationship("ApplicationVersion")
