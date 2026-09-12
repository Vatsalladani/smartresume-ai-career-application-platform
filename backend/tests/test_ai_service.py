from app.schemas.ai import ATSAnalysisPayload
from app.services.ai_service import analyze_resume


def test_local_analysis_returns_valid_scores() -> None:
    payload = ATSAnalysisPayload(
        job_title="Backend Engineer",
        job_description="We need Python FastAPI PostgreSQL SQLAlchemy Docker testing APIs.",
        resume_text=None,
    )
    result = analyze_resume(
        payload,
        "Backend Engineer\nSkills\nPython FastAPI PostgreSQL\nExperience\nBuilt APIs and improved latency by 30%.",
    )
    assert 0 <= result.original_score <= 100
    assert 0 <= result.predicted_ats_score <= 100
    assert result.keyword_report
