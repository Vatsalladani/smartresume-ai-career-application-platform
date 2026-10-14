"""Public Platform Configuration and Status Router for SmartResume.ai.

Serves candidate-facing public settings, feature flags, maintenance status,
and announcements with zero authentication required.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.services import platform_config_service

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/config", response_model=dict)
def get_public_platform_config(db: Session = Depends(get_db)) -> dict:
    """Returns safe public platform configuration, feature flags, template catalog, and announcements."""
    config = platform_config_service.get_public_config(db)
    return success_response(config, "Public platform configuration retrieved successfully.")
