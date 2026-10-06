from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class InterviewSessionCreate(BaseModel):
    job_id: Optional[int] = None
    version_id: Optional[int] = None
    resume_id: Optional[int] = None
    target_role: str = Field(default="", max_length=150)
    target_company: str = Field(default="", max_length=150)
    target_location: Optional[str] = Field(default=None, max_length=150)
    job_description: Optional[str] = None
    session_mode: str = Field(default="TEXT", max_length=20)  # TEXT, LIVE
    career_level: Optional[str] = Field(default="DEVELOPING", max_length=30)  # EARLY_CAREER, DEVELOPING, EXPERIENCED
    difficulty: str = Field(default="MEDIUM", max_length=30)  # EASY, MEDIUM, HARD, VERY_HARD, ADAPTIVE
    practice_mode: str = Field(default="STANDARD", max_length=30)  # QUICK, STANDARD, DEEP, FULL_PRESSURE


class PreparationGuideOut(BaseModel):
    target_role: str
    target_company: str
    resume_id: Optional[int] = None
    resume_title: Optional[str] = None
    most_relevant_topics: list[str] = Field(default_factory=list)
    likely_interview_areas: list[dict[str, str]] = Field(default_factory=list)
    weak_areas_to_revise: list[str] = Field(default_factory=list)
    eligibility_gap: Optional[dict[str, str]] = None
    practice_questions: list[dict[str, str]] = Field(default_factory=list)
    claims_to_defend: list[dict[str, Any]] = Field(default_factory=list)
    role_expectations: Optional[dict[str, Any]] = None
    preparation_checklist: list[dict[str, str]] = Field(default_factory=list)
    company_context_note: str = ""
    disclaimer: str = (
        "Likely interview areas based on public role patterns and company profile. "
        "Questions are designed for realistic practice and preparation. Actual employer interview questions may vary."
    )



class ClaimsToDefendOut(BaseModel):
    claim: str
    category: str
    why_asked: str
    evidence: str
    suggested_question: str


class LiveConfigOut(BaseModel):
    configured: bool
    model_name: Optional[str] = None
    message: str

    model_config = {"protected_namespaces": ()}



class InterviewMessageCreate(BaseModel):
    message_text: str = Field(min_length=1, max_length=10000)
    sender: str = Field(default="USER", max_length=10)


class InterviewMessageOut(BaseModel):
    id: int
    session_id: int
    sender: str
    message_text: str
    audio_url: Optional[str] = None
    evaluation_json: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewEvaluationOut(BaseModel):
    id: int
    session_id: int
    overall_score: int = 70
    technical_score: int = 70
    problem_solving_score: int = 70
    communication_score: int = 70
    resume_knowledge_score: int = 70
    role_readiness_score: int = 70
    holding_back: str = ""
    strong_areas: list[str] = Field(default_factory=list)
    needs_practice: list[str] = Field(default_factory=list)
    technical_gaps: list[str] = Field(default_factory=list)
    communication_improvements: list[str] = Field(default_factory=list)
    resume_claims_to_defend: list[dict] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    weak_questions: list[dict] = Field(default_factory=list)
    technical_topics_to_revise: list[str] = Field(default_factory=list)
    suggested_next_practice: str = ""
    readiness_level: str = "NEEDS_PRACTICE"
    created_at: datetime

    model_config = {"from_attributes": True}



class InterviewSessionOut(BaseModel):
    id: int
    user_id: int
    job_id: Optional[int] = None
    version_id: Optional[int] = None
    resume_id: Optional[int] = None
    resume_title: Optional[str] = None
    target_role: str
    target_company: str
    session_mode: str
    status: str
    readiness_score: int
    feedback_summary: str
    job_description_snapshot: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[InterviewMessageOut] = Field(default_factory=list)
    evaluation: Optional[InterviewEvaluationOut] = None

    model_config = {"from_attributes": True}
