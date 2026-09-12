from typing import Optional, Any
from pydantic import BaseModel, Field


class ApplicationPackGenerateRequest(BaseModel):
    version_id: int
    job_id: Optional[int] = None
    tone: str = Field(default="professional", max_length=50)
    target_geography: str = Field(default="", max_length=100)


class RecruiterEmailDraft(BaseModel):
    subject: str = ""
    recipient_role: str = ""
    body: str = ""
    gmail_url: str = ""


class ApplicationPackOut(BaseModel):
    version_id: int
    job_id: Optional[int] = None
    job_title: str = ""
    company: str = ""
    resume_snapshot: dict = Field(default_factory=dict)
    cover_letter: str = ""
    recruiter_email: RecruiterEmailDraft = Field(default_factory=RecruiterEmailDraft)
    application_answers: list[dict] = Field(default_factory=list)  # [{"question": "...", "answer": "...", "grounding": "..."}]
    application_checklist: list[dict] = Field(default_factory=list)  # [{"item": "...", "status": "READY/WARNING", "tip": "..."}]
    follow_up_strategy: dict = Field(default_factory=dict)  # {"days_after": 5, "suggested_date": "...", "template": "..."}
    thank_you_note: str = ""
    interview_prep_brief: dict = Field(default_factory=dict)  # {"claims_to_defend": [...], "likely_questions": [...]}
    risk_and_honesty_check: dict = Field(default_factory=dict)  # {"unsupported_claims": [...], "risk_level": "LOW"}
