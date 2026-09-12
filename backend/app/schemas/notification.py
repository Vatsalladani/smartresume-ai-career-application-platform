from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=5000)
    type: str = Field(default="INFO", max_length=50)  # TRIAL, JOB_MATCH, PROFILE_WIN, FOLLOW_UP, INTERVIEW, BILLING, INFO
    action_url: str = Field(default="", max_length=255)


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool
    action_url: str
    created_at: datetime

    model_config = {"from_attributes": True}
