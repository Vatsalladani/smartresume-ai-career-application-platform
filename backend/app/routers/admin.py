"""Admin Management API Router for SmartResume.ai.

Strict Role-Based Access Control:
- All GET endpoints require an authenticated administrator session (`require_admin`).
- All mutation endpoints (POST/PUT/DELETE) require write privileges (`require_admin_mutation`),
  blocking READONLY_ADMIN with 403 Forbidden.
- Role management & promotions require OWNER_ADMIN (`require_owner_admin`).
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import require_admin, require_admin_mutation, require_owner_admin
from app.models.admin import AdminAccount
from app.models.user import User
from app.services import admin_service, platform_config_service

router = APIRouter(prefix="/admin", tags=["admin"])


# Request Schemas
class RoleUpdatePayload(BaseModel):
    role: str = Field(..., description="'ADMIN' or 'USER'")


class UserStatusPayload(BaseModel):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserPlanPayload(BaseModel):
    plan_name: str = Field(..., description="'FREE', 'PRO', or 'EXECUTIVE'")


class FeatureFlagsUpdatePayload(BaseModel):
    flags: dict[str, bool] = Field(..., description="Key-value mapping of feature flags")


class TemplateStatusPayload(BaseModel):
    enabled: bool = Field(..., description="Whether the template is enabled")


class AIConfigUpdatePayload(BaseModel):
    gemini_primary_model: Optional[str] = None
    gemini_force_deterministic_fallback: Optional[bool] = None
    gemini_temperature: Optional[float] = None
    gemini_timeout_seconds: Optional[int] = None


class QuotasUpdatePayload(BaseModel):
    quota_free_resumes: Optional[int] = None
    quota_free_tailors: Optional[int] = None
    quota_free_exports: Optional[int] = None
    quota_free_analyses: Optional[int] = None


class InterviewConfigPayload(BaseModel):
    interview_default_duration: Optional[int] = Field(default=None, ge=5, le=180)
    interview_max_duration: Optional[int] = Field(default=None, ge=10, le=240)
    strict_focus_max_warnings: Optional[int] = Field(default=None, ge=1, le=10)
    strict_focus_mode_enabled: Optional[bool] = None
    voice_interview_enabled: Optional[bool] = None
    text_interview_enabled: Optional[bool] = None
    quota_pro_tailors: Optional[int] = None
    quota_pro_exports: Optional[int] = None


class AnnouncementPayload(BaseModel):
    enabled: bool
    text: str


# 1. Platform Overview
@router.get("/overview", response_model=dict)
def get_platform_overview(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Returns platform health, user statistics, document volume, subscription breakdown, and AI telemetry summary."""
    data = admin_service.get_admin_overview(db)
    return success_response(data, "Admin overview metrics retrieved successfully.")


# 2. User Directory & Management
@router.get("/users", response_model=dict)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Lists registered users with pagination, role indicators, subscription plan, and resume counts."""
    data = admin_service.list_admin_users(db, page=page, page_size=page_size, search=search)
    return success_response(data, "User directory retrieved successfully.")


@router.post("/users/{user_id}/role", response_model=dict)
def update_user_role(
    user_id: int,
    payload: RoleUpdatePayload,
    current_admin: AdminAccount | User = Depends(require_owner_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Updates a user's role to ADMIN or USER with audit trail. Restricted to OWNER_ADMIN."""
    data = admin_service.update_user_role(db, user_id=user_id, new_role=payload.role, admin_actor=current_admin)
    return success_response(data, "User role successfully updated.")


@router.post("/users/{user_id}/status", response_model=dict)
def update_user_status(
    user_id: int,
    payload: UserStatusPayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Updates a user's active/suspended status or email verified state."""
    data = admin_service.update_user_status(
        db,
        user_id=user_id,
        is_active=payload.is_active,
        is_verified=payload.is_verified,
        admin_actor=current_admin,
    )
    return success_response(data, "User status updated successfully.")


@router.post("/users/{user_id}/plan", response_model=dict)
def update_user_plan(
    user_id: int,
    payload: UserPlanPayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Sets a user's subscription plan directly from the admin console."""
    data = admin_service.update_user_plan(
        db,
        user_id=user_id,
        new_plan=payload.plan_name,
        admin_actor=current_admin,
    )
    return success_response(data, "User subscription plan updated successfully.")


# 3. Resume & Template Management
@router.get("/resumes", response_model=dict)
def list_resumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Lists resumes across all candidates with ATS score, target role, and versions."""
    data = admin_service.list_admin_resumes(db, page=page, page_size=page_size, search=search)
    return success_response(data, "Resumes directory retrieved successfully.")


@router.get("/resumes/{resume_id}", response_model=dict)
def get_resume_detail(
    resume_id: int,
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves full resume inspection snapshot including parsed JSON content and version history."""
    data = admin_service.get_admin_resume_detail(db, resume_id=resume_id)
    return success_response(data, "Resume details retrieved successfully.")


@router.get("/templates", response_model=dict)
def get_templates(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves available resume templates and their enabled/disabled state."""
    data = admin_service.get_templates_status(db)
    return success_response(data, "Template status retrieved successfully.")


@router.post("/templates/{template_id}/status", response_model=dict)
def set_template_status(
    template_id: str,
    payload: TemplateStatusPayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Enables or disables a resume template globally."""
    data = admin_service.update_template_status(
        db,
        template_id=template_id,
        enabled=payload.enabled,
        admin_actor=current_admin,
    )
    return success_response(data, "Template status updated successfully.")


# 4. AI Orchestration & Live Controls
@router.get("/ai-ops", response_model=dict)
def get_ai_operations_telemetry(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves real AI model telemetry, fallback rate, latency percentiles, and feature usage."""
    data = admin_service.get_ai_ops_telemetry(db)
    return success_response(data, "AI operations telemetry retrieved successfully.")


@router.get("/ai-config", response_model=dict)
def get_ai_config(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves AI model configuration including primary model and fallback kill switch."""
    data = admin_service.get_ai_config(db)
    return success_response(data, "AI configuration retrieved successfully.")


@router.put("/ai-config", response_model=dict)
def update_ai_config(
    payload: AIConfigUpdatePayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Updates AI model configuration with immediate live propagation and audit logging."""
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    data = admin_service.update_ai_config(db, config_data=update_data, admin_actor=current_admin)
    return success_response(data, "AI configuration updated successfully.")


# 5. Feature Flags & Runtime Configuration
@router.get("/feature-flags", response_model=dict)
def get_feature_flags(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves current feature flags backed by PostgreSQL platform_settings."""
    flags = admin_service.get_feature_flags(db)
    return success_response(flags, "Feature flags retrieved successfully.")


@router.put("/feature-flags", response_model=dict)
def update_feature_flags(
    payload: FeatureFlagsUpdatePayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Updates system feature flags with database persistence and audit trail."""
    updated = admin_service.update_feature_flags(payload.flags, admin_actor=current_admin, db=db)
    return success_response(updated, "Feature flags updated successfully.")


# 6. Subscriptions & Quota Management
@router.get("/subscriptions", response_model=dict)
def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves paginated user subscriptions."""
    data = admin_service.list_admin_subscriptions(db, page=page, page_size=page_size, search=search)
    return success_response(data, "Subscriptions retrieved successfully.")


@router.get("/quotas", response_model=dict)
def get_quotas(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves default plan quotas."""
    data = admin_service.get_quotas_config(db)
    return success_response(data, "Plan quotas retrieved successfully.")


@router.put("/quotas", response_model=dict)
def update_quotas(
    payload: QuotasUpdatePayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Updates default plan quotas with immediate effect."""
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    data = admin_service.update_quotas_config(db, quotas_data=update_data, admin_actor=current_admin)
    return success_response(data, "Plan quotas updated successfully.")


# 7. Announcements & Maintenance
@router.get("/announcement", response_model=dict)
def get_announcement(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves current platform announcement banner status."""
    enabled = platform_config_service.get_setting("system_announcement_enabled", False, db=db)
    text = platform_config_service.get_setting("system_announcement_text", "", db=db)
    return success_response({"enabled": enabled, "text": text}, "Announcement retrieved successfully.")


@router.put("/announcement", response_model=dict)
def update_announcement(
    payload: AnnouncementPayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Updates platform announcement banner with live propagation."""
    platform_config_service.set_setting(
        db, key="system_announcement_enabled", value=payload.enabled, actor_email=admin_service.get_actor_email(current_admin)
    )
    platform_config_service.set_setting(
        db, key="system_announcement_text", value=payload.text, actor_email=admin_service.get_actor_email(current_admin)
    )
    return success_response({"enabled": payload.enabled, "text": payload.text}, "Announcement banner updated successfully.")


# 8. Interview Simulator Engine Configuration
@router.get("/interview-config", response_model=dict)
def get_interview_config(
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves current interview simulator engine settings and limits."""
    cfg = {
        "interview_default_duration": platform_config_service.get_setting("interview_default_duration", 60, db=db),
        "interview_max_duration": platform_config_service.get_setting("interview_max_duration", 120, db=db),
        "strict_focus_max_warnings": platform_config_service.get_setting("strict_focus_max_warnings", 3, db=db),
        "strict_focus_mode_enabled": platform_config_service.get_setting("strict_focus_mode_enabled", True, db=db),
        "voice_interview_enabled": platform_config_service.get_setting("voice_interview_enabled", True, db=db),
        "text_interview_enabled": platform_config_service.get_setting("text_interview_enabled", True, db=db),
    }
    return success_response(cfg, "Interview configuration retrieved successfully.")


@router.put("/interview-config", response_model=dict)
def update_interview_config(
    payload: InterviewConfigPayload,
    current_admin: AdminAccount | User = Depends(require_admin_mutation),
    db: Session = Depends(get_db),
) -> dict:
    """Updates interview simulator engine settings with persistence and audit trail."""
    actor_email = admin_service.get_actor_email(current_admin)
    updated = {}
    for key, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            platform_config_service.set_setting(db, key=key, value=val, actor_email=actor_email)
            updated[key] = val

    admin_service.log_admin_action(
        db=db,
        actor_email=actor_email,
        action="INTERVIEW_CONFIG_UPDATED",
        details=f"Updated interview settings: {updated}",
        severity="INFO",
    )
    return success_response(updated, "Interview engine configuration updated successfully.")


# 9. Security Audit Logs
@router.get("/audit-logs", response_model=dict)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    search: str = Query("", max_length=100),
    current_admin: AdminAccount | User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves recent security and administrative audit event logs from PostgreSQL."""
    logs = admin_service.get_audit_logs(db=db, limit=limit, search=search)
    return success_response(logs, "Security audit logs retrieved successfully.")
