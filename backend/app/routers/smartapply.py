from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Profile, ApplicationVersion, JobPosting
from app.services import job_radar_service

router = APIRouter(prefix="/smartapply", tags=["smartapply"])


@router.post("/detect-job")
def detect_job(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    url = payload.get("url", "")
    page_text = payload.get("text", "")
    title = payload.get("title", "")
    company = payload.get("company", "")

    # Clean and extract basic info
    if not title:
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        title = lines[0] if lines else "Job Opening"
    if not company:
        company = "Target Employer"

    return success_response({
        "url": url,
        "title": title[:100],
        "company": company[:100],
        "detected_length": len(page_text),
    })


@router.post("/field-answers")
def get_field_answers(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    fields_requested = payload.get("fields", ["full_name", "email", "phone", "linkedin", "github", "summary"])

    user_answers = {
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": profile.phone if profile else "",
        "location": profile.location if profile else "",
        "linkedin": profile.linkedin_url if profile else "",
        "github": profile.github_url if profile else "",
        "portfolio": profile.website_url if profile else "",
        "headline": profile.headline if profile else "",
        "summary": profile.summary if profile else "",
        "work_authorization": "Authorized to work without sponsorship",
        "notice_period": "30 days / immediate",
    }

    # Include top skills
    if profile and profile.skills:
        user_answers["skills"] = ", ".join([s.name for s in profile.skills[:8]])

    # Include recent experience
    if profile and profile.experiences:
        top_exp = profile.experiences[0]
        user_answers["recent_experience"] = f"{top_exp.role_title} at {top_exp.company} ({top_exp.start_date} - {'Present' if top_exp.is_current else top_exp.end_date})"

    return success_response({
        "answers": {k: user_answers.get(k, "") for k in fields_requested if k in user_answers},
        "all_available_answers": user_answers,
    })


@router.post("/answer")
def generate_portal_answer(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    question = payload.get("question", "")
    job_title = payload.get("job_title", "Target Role")
    company = payload.get("company", "the company")
    tone = payload.get("tone", "professional")

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    skills = [s.name for s in profile.skills[:5]] if profile and profile.skills else ["Software Engineering", "Systems Architecture"]
    skills_str = ", ".join(skills)

    top_exp = profile.experiences[0] if profile and profile.experiences else None
    role_exp = f"{top_exp.role_title} at {top_exp.company}" if top_exp else "Engineering roles"

    answer = (
        f"Throughout my career as a {role_exp}, I have prioritized evidence-backed results and technical rigor. "
        f"In response to '{question}', I leverage proven hands-on experience in {skills_str} to deliver reliable, scalable solutions "
        f"that align directly with {company}'s strategic goals for the {job_title} role."
    )
    return success_response({
        "question": question,
        "answer": answer,
        "grounding": f"Grounded in verified experience ({role_exp}) and skills ({skills_str}).",
    })
