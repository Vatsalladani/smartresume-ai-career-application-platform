from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


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


# ============================================================
# IMPROVE RESUME WORKSPACE SCHEMAS
# ============================================================

class ImprovementSuggestion(BaseModel):
    id: str
    section: str  # "summary", "headline", "experience", "projects", "skills", "education", "certifications", "header"
    target_id: str | None = None
    target_index: int | None = None
    sub_index: int | None = None
    priority: str = "MEDIUM"  # "HIGH", "MEDIUM", "LOW"
    problem: str
    why: str
    current: str = ""
    suggested: str = ""
    before: str = ""
    after: str = ""
    evidence: list[str] = []
    risk: str = "Safe"
    change_type: str = "wording"  # "wording", "clarity", "buzzword_removal", "relevance", "formatting", "structure"
    confidence: float = 0.95
    action: str = "apply"
    status: str = "pending"  # "pending", "applied", "kept", "undone"

    @model_validator(mode="before")
    @classmethod
    def sync_before_after(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "before" in data and not data.get("current"):
                data["current"] = data["before"]
            elif "current" in data and not data.get("before"):
                data["before"] = data["current"]

            if "after" in data and not data.get("suggested"):
                data["suggested"] = data["after"]
            elif "suggested" in data and not data.get("after"):
                data["after"] = data["suggested"]
        return data


class JobRequirementMatch(BaseModel):
    requirement: str
    status: str = "NOT CURRENTLY DEMONSTRATED"  # "CLEARLY DEMONSTRATED", "PARTIALLY DEMONSTRATED", "NOT CURRENTLY DEMONSTRATED", "NOT ENOUGH INFORMATION", or legacy "covered", "partial", "not_demonstrated", "eligibility_gap"
    evidence: str | None = None
    gap_type: str | None = None  # "wording_issue", "evidence_gap", "eligibility_gap", "missing_skill", "missing_requirement", "insufficient_information"
    recommendation: str | None = None
    note: str | None = None


class JobAlignmentSummary(BaseModel):
    role: str | None = None
    seniority: str | None = None
    years_experience: str | None = None
    must_have_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    tools: list[str] = []
    technologies: list[str] = []
    domain: str | None = None
    education_requirements: list[str] = []
    certifications: list[str] = []
    location: str | None = None
    work_authorization: str | None = None
    other_constraints: list[str] = []
    is_role_only: bool = False
    role_expectations_note: str | None = None
    potential_concerns: list[str] = []
    suggested_actions: list[str] = []
    match_score: int | None = None
    requirements: list[JobRequirementMatch] = []
    covered: list[JobRequirementMatch] = []
    partial: list[JobRequirementMatch] = []
    not_demonstrated: list[JobRequirementMatch] = []
    eligibility_gaps: list[JobRequirementMatch] = []


class ImproveResumePayload(BaseModel):
    resume_id: int
    mode: str = "general"  # "general" or "job"
    target_role: str | None = None
    target_company: str | None = None
    job_description: str | None = None


class ImproveResumeResponse(BaseModel):
    resume_id: int
    resume_title: str
    domain: str
    career_stage: str
    target_role: str | None = None
    target_company: str | None = None
    canonical_score: int
    job_match_score: int | None = None
    score_label: str
    stage_label: str
    overall_summary: str
    analysis_status: str = "completed"  # "completed", "failed", "no_content"
    state: str = "STATE_1"  # "STATE_1", "STATE_2", "STATE_3", "STATE_4", "STATE_5"
    status_message: str | None = None
    analyzed_sections: dict[str, int] = {}
    top_improvements: list[dict[str, Any]] = []
    suggestions: list[ImprovementSuggestion] = []
    job_alignment: JobAlignmentSummary | None = None
    active_resumes: list[dict[str, Any]] = []


class ApplyImprovementItem(BaseModel):
    id: str
    section: str
    target_id: str | None = None
    target_index: int | None = None
    sub_index: int | None = None
    suggested: str
    current: str


class ApplyImprovementPayload(BaseModel):
    resume_id: int
    suggestions: list[ApplyImprovementItem]


class ApplyImprovementResponse(BaseModel):
    resume_id: int
    applied_count: int
    version_id: int
    version_number: int
    previous_score: int
    new_score: int
    score_delta: int
    what_improved: list[str] = []
    updated_resume: dict[str, Any]


class UndoImprovementPayload(BaseModel):
    resume_id: int
    version_id: int | None = None
    suggestion_id: str | None = None
    section: str | None = None
    target_index: int | None = None
    sub_index: int | None = None
    original_text: str | None = None


class UndoImprovementResponse(BaseModel):
    resume_id: int
    restored: bool
    new_score: int
    updated_resume: dict[str, Any]

