from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, ApplicationVersion
from app.schemas.application_pack import ApplicationPackGenerateRequest, ApplicationPackOut
from app.services import application_pack_service

router = APIRouter(prefix="/application-pack", tags=["application-pack"])


@router.post("/generate")
def generate_pack(
    payload: ApplicationPackGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        pack = application_pack_service.generate_application_pack(
            db=db,
            user_id=current_user.id,
            version_id=payload.version_id,
            job_id=payload.job_id,
            tone=payload.tone,
            target_geography=payload.target_geography or "India",
        )
        return success_response(pack, "Complete Application Pack generated.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{version_id}")
def get_pack(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    version = (
        db.query(ApplicationVersion)
        .join(JobPosting, ApplicationVersion.job_id == JobPosting.id)
        .filter(
            ApplicationVersion.id == version_id,
            JobPosting.user_id == current_user.id,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")

    if not version.application_pack:
        # Generate dynamically if missing
        pack = application_pack_service.generate_application_pack(
            db=db,
            user_id=current_user.id,
            version_id=version_id,
            job_id=version.job_id,
        )
        return success_response(pack)

    return success_response(version.application_pack)
