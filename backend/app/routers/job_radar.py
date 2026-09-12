from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services import job_radar_service

router = APIRouter(prefix="/job-radar", tags=["job-radar"])


@router.get("")
def search_radar(
    query: Optional[str] = "",
    location: Optional[str] = "",
    country: Optional[str] = "",
    domain: Optional[str] = "",
    experience_level: Optional[str] = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = job_radar_service.search_job_radar(
        db=db,
        user_id=current_user.id,
        query=query or "",
        location=location or "",
        country=country or "",
        domain=domain or "",
        experience_level=experience_level or "",
    )
    return success_response(result.model_dump())
