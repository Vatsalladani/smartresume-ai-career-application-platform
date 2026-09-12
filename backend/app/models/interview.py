from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True)
    version_id: Mapped[int | None] = mapped_column(ForeignKey("application_versions.id", ondelete="SET NULL"), nullable=True)
    target_role: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    target_company: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    session_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="TEXT")  # TEXT, VOICE
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, CANCELLED
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="interview_sessions")
    job = relationship("JobPosting")
    version = relationship("ApplicationVersion")
    messages = relationship("InterviewMessage", back_populates="session", cascade="all, delete-orphan", order_by="InterviewMessage.created_at")
    evaluation = relationship("InterviewEvaluation", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(10), nullable=False)  # "AI", "USER"
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluation_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="messages")


class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    strong_areas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    needs_practice: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    technical_gaps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    communication_improvements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    resume_claims_to_defend: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suggested_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    readiness_level: Mapped[str] = mapped_column(String(30), nullable=False, default="NEEDS_PRACTICE")  # READY, STRONG, NEEDS_PRACTICE
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="evaluation")
