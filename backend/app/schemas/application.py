from datetime import datetime

from pydantic import BaseModel, Field, model_validator
from typing import Any


class JobApplicationCreate(BaseModel):
    company: str = Field(min_length=2, max_length=150)
    job_title: str = Field(min_length=2, max_length=150)
    job_url: str | None = Field(default=None, max_length=500)
    job_description: str | None = Field(default=None, max_length=80_000)
    resume_id: int | None = None
    job_posting_id: int | None = None
    version_id: int | None = None
    status: str = Field(default="SAVED", max_length=30)
    location: str = Field(default="", max_length=150)
    work_arrangement: str = Field(default="", max_length=50)
    source: str = Field(default="", max_length=100)
    applied_date: str = Field(default="", max_length=50)
    deadline_date: str = Field(default="", max_length=50)
    salary_range: str = Field(default="", max_length=100)
    contact_name: str = Field(default="", max_length=150)
    contact_email: str = Field(default="", max_length=150)
    contact_phone: str = Field(default="", max_length=50)
    is_archived: bool = False
    notes: str | None = Field(default=None, max_length=10_000)
    next_action: str | None = Field(default=None, max_length=150)
    next_action_at: datetime | None = None

    cover_letter_text: str = ""
    email_draft_json: dict = Field(default_factory=dict)
    application_answers_json: dict = Field(default_factory=dict)
    follow_up_date: str = ""
    interview_date: str = ""
    interview_notes: str = ""
    outcome: str = ""

    @model_validator(mode="before")
    @classmethod
    def clean_application(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "company_name" in data and ("company" not in data or not data.get("company")):
                data["company"] = data["company_name"]
            if "position_title" in data and ("job_title" not in data or not data.get("job_title")):
                data["job_title"] = data["position_title"]
            if "position" in data and ("job_title" not in data or not data.get("job_title")):
                data["job_title"] = data["position"]
            if "job_id" in data and ("job_posting_id" not in data or not data.get("job_posting_id")):
                data["job_posting_id"] = data["job_id"]
        return data


class JobApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=2, max_length=150)
    job_title: str | None = Field(default=None, min_length=2, max_length=150)
    job_url: str | None = Field(default=None, max_length=500)
    job_description: str | None = Field(default=None, max_length=80_000)
    resume_id: int | None = None
    job_posting_id: int | None = None
    version_id: int | None = None
    status: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=150)
    work_arrangement: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    applied_date: str | None = Field(default=None, max_length=50)
    deadline_date: str | None = Field(default=None, max_length=50)
    salary_range: str | None = Field(default=None, max_length=100)
    contact_name: str | None = Field(default=None, max_length=150)
    contact_email: str | None = Field(default=None, max_length=150)
    contact_phone: str | None = Field(default=None, max_length=50)
    is_archived: bool | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    next_action: str | None = Field(default=None, max_length=150)
    next_action_at: datetime | None = None
    cover_letter_text: str | None = None
    email_draft_json: dict | None = None
    application_answers_json: dict | None = None
    follow_up_date: str | None = None
    interview_date: str | None = None
    interview_notes: str | None = None
    outcome: str | None = None

    @model_validator(mode="before")
    @classmethod
    def clean_update(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "company_name" in data and ("company" not in data or not data.get("company")):
                data["company"] = data["company_name"]
            if "position_title" in data and ("job_title" not in data or not data.get("job_title")):
                data["job_title"] = data["position_title"]
            if "position" in data and ("job_title" not in data or not data.get("job_title")):
                data["job_title"] = data["position"]
            if "job_id" in data and ("job_posting_id" not in data or not data.get("job_posting_id")):
                data["job_posting_id"] = data["job_id"]
        return data


class JobApplicationOut(BaseModel):
    id: int
    resume_id: int | None
    resume_title: str | None = None
    job_posting_id: int | None = None
    version_id: int | None = None
    company: str
    job_title: str
    job_url: str | None
    job_description: str | None
    status: str
    location: str = ""
    work_arrangement: str = ""
    source: str = ""
    applied_date: str = ""
    deadline_date: str = ""
    salary_range: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    is_archived: bool = False
    notes: str | None
    next_action: str | None
    next_action_at: datetime | None
    cover_letter_text: str = ""
    email_draft_json: dict = Field(default_factory=dict)
    application_answers_json: dict = Field(default_factory=dict)
    follow_up_date: str = ""
    interview_date: str = ""
    interview_notes: str = ""
    outcome: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobWorkspaceOut(BaseModel):
    application: JobApplicationOut
    resume: dict[str, Any] | None = None
    job_posting: dict[str, Any] | None = None
    preparation_guide: dict[str, Any] | None = None
    claims_to_defend: list[dict[str, Any]] = Field(default_factory=list)
    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)

