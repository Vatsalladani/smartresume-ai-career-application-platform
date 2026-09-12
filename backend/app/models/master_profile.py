from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    headline: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    linkedin_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    github_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_domain: Mapped[str] = mapped_column(String(100), nullable=False, default="Software Engineering")
    career_level: Mapped[str] = mapped_column(String(50), nullable=False, default="DEVELOPING_PROFESSIONAL")
    target_geography: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    preferred_industries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    health_report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    consistency_graph: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="master_profile")
    experiences = relationship("Experience", back_populates="profile", cascade="all, delete-orphan", order_by="Experience.order_index")
    projects = relationship("Project", back_populates="profile", cascade="all, delete-orphan", order_by="Project.order_index")
    education = relationship("Education", back_populates="profile", cascade="all, delete-orphan", order_by="Education.order_index")
    skills = relationship("Skill", back_populates="profile", cascade="all, delete-orphan", order_by="Skill.order_index")
    certifications = relationship("Certification", back_populates="profile", cascade="all, delete-orphan")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(150), nullable=False)
    role_title: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Full-time")
    start_date: Mapped[str] = mapped_column(String(30), nullable=False)
    end_date: Mapped[str] = mapped_column(String(30), nullable=False, default="Present")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bullet_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    technologies_used: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="experiences")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    role_title: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    repo_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    start_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    end_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bullet_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    technologies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="projects")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[str] = mapped_column(String(150), nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    start_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    end_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    grade: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    activities_societies: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="education")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="technical")
    proficiency: Mapped[str] = mapped_column(String(30), nullable=False, default="Intermediate")
    years_of_experience: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_top_skill: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNSUPPORTED")
    evidence_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    relevance_status: Mapped[str] = mapped_column(String(30), nullable=False, default="KEEP")
    relevance_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    profile = relationship("Profile", back_populates="skills")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str] = mapped_column(String(150), nullable=False)
    issue_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    expiration_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    credential_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    credential_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    profile = relationship("Profile", back_populates="certifications")
