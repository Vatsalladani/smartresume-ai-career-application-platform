from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KeywordInsight(BaseModel):
    keyword: str
    importance: int = Field(ge=1, le=5)
    present: bool
    recommendation: str


class ATSBreakdown(BaseModel):
    keyword_match: int = Field(ge=0, le=100)
    formatting: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)


class EnhancedSections(BaseModel):
    summary: str
    skills: list[str]
    experience: list[dict[str, Any]]


class ATSAnalysisPayload(BaseModel):
    resume_id: int | None = None
    resume_text: str | None = Field(default=None, max_length=120_000)
    job_description: str = Field(min_length=40, max_length=80_000)
    job_title: str | None = Field(default=None, max_length=150)


class ATSAnalysisResult(BaseModel):
    original_score: int = Field(ge=0, le=100)
    predicted_ats_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    breakdown: ATSBreakdown
    weak_words_removed: list[str]
    action_verbs_added: list[str]
    missing_critical_keywords: list[str]
    keyword_report: list[KeywordInsight]
    missing_skills_report: list[str]
    recruiter_checklist: list[str]
    grammar_suggestions: list[str]
    duplicate_content_warnings: list[str]
    quantified_achievement_suggestions: list[str]
    enhanced_sections: EnhancedSections
    prompt_injection_warnings: list[str] = []
    engine: str = "local"


class ATSAnalysisOut(BaseModel):
    id: int
    resume_id: int | None
    job_title: str | None
    job_description: str
    original_score: int
    predicted_ats_score: int
    confidence_score: int
    keyword_report: dict[str, Any]
    suggestions: dict[str, Any]
    enhanced_content: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewQuestionRequest(BaseModel):
    resume_id: int | None = None
    resume_text: str | None = Field(default=None, max_length=120_000)
    job_description: str = Field(min_length=40, max_length=80_000)


class CoverLetterRequest(InterviewQuestionRequest):
    company: str = Field(min_length=2, max_length=150)
    job_title: str = Field(min_length=2, max_length=150)


class LinkedInSummaryRequest(BaseModel):
    resume_id: int | None = None
    resume_text: str | None = Field(default=None, max_length=120_000)
