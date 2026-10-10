"""Schemas for Dedicated Admin Authentication and Invitations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    email_or_username: str = Field(..., description="Administrator email or username")
    password: str = Field(..., min_length=1, max_length=128)


class AdminSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., description="Administrator email address")
    password: str = Field(..., min_length=8, max_length=128)
    invitation_token: str = Field(..., min_length=8, max_length=255, description="Invitation token provided by Owner Admin")


class AdminInvitationCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the administrator being invited")
    role: str = Field("ADMIN", description="'ADMIN' or 'READONLY_ADMIN'")
    expires_in_hours: int = Field(72, ge=1, le=720, description="Hours until invitation expiration")


class AdminOut(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminOut


class AdminInvitationOut(BaseModel):
    id: int
    email: str
    role: str
    expires_at: datetime
    is_consumed: bool
    created_at: datetime
    invite_url: Optional[str] = None
    raw_token: Optional[str] = None

    class Config:
        from_attributes = True
