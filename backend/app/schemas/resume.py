from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ResumeCreate(BaseModel):
    title: str = Field(default="My Resume", max_length=150)
    status: str = Field(default="Draft", max_length=30)
    target_role: str | None = Field(default=None, max_length=150)
    target_company: str | None = Field(default=None, max_length=150)
    target_location: str | None = Field(default=None, max_length=150)
    target_market: str = Field(default="Global", max_length=50)
    document_purpose: str = Field(default="Professional Resume", max_length=50)
    ats_mode: str = Field(default="ATS-Safe", max_length=30)
    target_job_id: int | None = None
    raw_text: str | None = None
    parsed_content: dict[str, Any] | None = None


class ResumeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    status: str | None = Field(default=None, max_length=30)
    target_role: str | None = Field(default=None, max_length=150)
    target_company: str | None = Field(default=None, max_length=150)
    target_location: str | None = Field(default=None, max_length=150)
    target_market: str | None = Field(default=None, max_length=50)
    document_purpose: str | None = Field(default=None, max_length=50)
    ats_mode: str | None = Field(default=None, max_length=30)
    target_job_id: int | None = None
    is_archived: bool | None = None
    raw_text: str | None = None
    parsed_content: dict[str, Any] | None = None


class ResumeOut(BaseModel):
    id: int
    title: str
    status: str = "Draft"
    target_role: str | None = None
    target_company: str | None = None
    target_location: str | None = None
    target_market: str = "Global"
    document_purpose: str = "Professional Resume"
    ats_mode: str = "ATS-Safe"
    target_job_id: int | None = None
    is_archived: bool = False
    ats_score: int
    completeness_score: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetail(ResumeOut):
    raw_text: str
    parsed_content: dict[str, Any]


class ResumeVersionOut(BaseModel):
    id: int
    resume_id: int
    version_number: int
    changelog: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeCompareOut(BaseModel):
    resume_id: int
    current_version: int
    compared_version: int
    additions: list[str]
    removals: list[str]


class ResumeScoreRequest(BaseModel):
    resume_id: int | None = None
    resume_data: dict[str, Any] | None = None
    target_role: str = Field(default="Software Engineer", max_length=150)
    target_company: str | None = Field(default=None, max_length=150)
    job_description: str | None = None
    career_level: str | None = None
    previous_score: int | None = None


class ResumeScoreOut(BaseModel):
    overall_score: int
    target_role: str
    target_company: str
    career_level: str
    is_fresher_calibrated: bool
    what_is_helping: list[str] = Field(default_factory=list)
    what_is_holding_back: list[str] = Field(default_factory=list)
    top_improvements: list[dict[str, Any]] = Field(default_factory=list)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    buzzwords_detected: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_skills: list[dict[str, Any]] = Field(default_factory=list)
    supported_skills_count: int = 0
    summary_consistency_notes: list[str] = Field(default_factory=list)
    eligibility_gaps: list[dict[str, Any]] = Field(default_factory=list)
    previous_score: int | None = None
    score_delta: int | None = None
    delta_explanation: str | None = None

