from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services import career_insights_service

router = APIRouter(prefix="/career-insights", tags=["career-insights"])


@router.get("")
def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    insights = career_insights_service.get_career_insights(db, current_user.id)
    return success_response(insights.model_dump())
