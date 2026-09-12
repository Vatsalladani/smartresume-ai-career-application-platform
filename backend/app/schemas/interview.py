from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class InterviewSessionCreate(BaseModel):
    job_id: Optional[int] = None
    version_id: Optional[int] = None
    target_role: str = Field(default="", max_length=150)
    target_company: str = Field(default="", max_length=150)
    session_mode: str = Field(default="TEXT", max_length=20)  # TEXT, LIVE
    career_level: Optional[str] = Field(default="DEVELOPING", max_length=30)  # EARLY_CAREER, DEVELOPING, EXPERIENCED


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
    strong_areas: list[str] = Field(default_factory=list)
    needs_practice: list[str] = Field(default_factory=list)
    technical_gaps: list[str] = Field(default_factory=list)
    communication_improvements: list[str] = Field(default_factory=list)
    resume_claims_to_defend: list[dict] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    readiness_level: str = "NEEDS_PRACTICE"
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewSessionOut(BaseModel):
    id: int
    user_id: int
    job_id: Optional[int] = None
    version_id: Optional[int] = None
    target_role: str
    target_company: str
    session_mode: str
    status: str
    readiness_score: int
    feedback_summary: str
    created_at: datetime
    updated_at: datetime
    messages: list[InterviewMessageOut] = Field(default_factory=list)
    evaluation: Optional[InterviewEvaluationOut] = None

    model_config = {"from_attributes": True}
