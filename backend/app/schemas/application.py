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
    job_posting_id: int | None = None
    version_id: int | None = None
    company: str
    job_title: str
    job_url: str | None
    job_description: str | None
    status: str
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
