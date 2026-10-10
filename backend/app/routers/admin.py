"""Admin Management API Router for SmartResume.ai.

Strict Role-Based Access Control:
All endpoints strictly require `current_user.role == 'ADMIN'` and return `403 Forbidden`
for standard authenticated users.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleUpdatePayload(BaseModel):
    role: str = Field(..., description="'ADMIN' or 'USER'")


class FeatureFlagsUpdatePayload(BaseModel):
    flags: dict[str, bool] = Field(..., description="Key-value mapping of feature flags")


@router.get("/overview", response_model=dict)
def get_platform_overview(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Returns platform health, user statistics, document volume, and AI telemetry summary."""
    data = admin_service.get_admin_overview(db)
    return success_response(data, "Admin overview metrics retrieved successfully.")


@router.get("/users", response_model=dict)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Lists registered users with pagination, role indicators, and resume counts."""
    data = admin_service.list_admin_users(db, page=page, page_size=page_size, search=search)
    return success_response(data, "User directory retrieved successfully.")


@router.post("/users/{user_id}/role", response_model=dict)
def update_user_role(
    user_id: int,
    payload: RoleUpdatePayload,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Updates a user's role to ADMIN or USER with audit trail."""
    data = admin_service.update_user_role(db, user_id=user_id, new_role=payload.role, admin_actor=current_admin)
    return success_response(data, "User role successfully updated.")


@router.get("/ai-ops", response_model=dict)
def get_ai_operations_telemetry(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieves AI model telemetry, fallback rate, latency percentiles, and feature usage."""
    data = admin_service.get_ai_ops_telemetry(db)
    return success_response(data, "AI operations telemetry retrieved successfully.")


@router.get("/feature-flags", response_model=dict)
def get_feature_flags(
    current_admin: User = Depends(require_admin),
) -> dict:
    """Retrieves current feature flags."""
    flags = admin_service.get_feature_flags()
    return success_response(flags, "Feature flags retrieved successfully.")


@router.put("/feature-flags", response_model=dict)
def update_feature_flags(
    payload: FeatureFlagsUpdatePayload,
    current_admin: User = Depends(require_admin),
) -> dict:
    """Updates system feature flags."""
    updated = admin_service.update_feature_flags(payload.flags, admin_actor=current_admin)
    return success_response(updated, "Feature flags updated successfully.")


@router.get("/audit-logs", response_model=dict)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    current_admin: User = Depends(require_admin),
) -> dict:
    """Retrieves recent security and administrative audit event logs."""
    logs = admin_service.get_audit_logs(limit=limit)
    return success_response(logs, "Security audit logs retrieved successfully.")
