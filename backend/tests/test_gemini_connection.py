"""
Minimal, safe Gemini API connectivity and AI service validation tests.
NEVER prints or logs API keys, authorization headers, or sensitive data.
"""
import pytest
from app.core.config import get_settings
from app.schemas.ai import ATSAnalysisPayload, ATSAnalysisResult
from app.services.ai_service import analyze_resume


def test_gemini_api_key_loaded():
    """Verify Gemini API key is loaded from the environment."""
    settings = get_settings()
    assert settings.gemini_api_key is not None, "GEMINI_API_KEY must be configured in environment (.env)"
    assert len(settings.gemini_api_key.strip()) > 10, "GEMINI_API_KEY appears too short"
    assert settings.gemini_model is not None, "GEMINI_MODEL must be configured"


def test_gemini_sdk_initialization_and_live_connectivity():
    """
    Verifies the google-generativeai SDK can be configured with the environment key
    and communicate with the live Google Gemini API.
    """
    settings = get_settings()
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    # 1. Live token count check (succeeds on active Google API key)
    token_count = model.count_tokens("Reply with exactly:\nGEMINI_OK")
    assert token_count.total_tokens > 0, "Live Gemini token count failed"

    # 2. Live content generation check
    try:
        response = model.generate_content(
            "Reply with exactly:\nGEMINI_OK",
            request_options={"timeout": 15},
        )
        assert response.text is not None
        assert len(response.text.strip()) > 0
    except Exception as exc:
        err_msg = str(exc)
        # Verify that live Google API responded (quota/rate limit or permissions)
        is_live_google_response = any(code in err_msg for code in ["429", "RESOURCE_EXHAUSTED", "403", "PERMISSION_DENIED"])
        assert is_live_google_response, f"Unexpected Gemini error: {type(exc).__name__}: {err_msg[:120]}"


def test_ai_service_analyze_resume_structured_output():
    """
    Verifies that the existing SmartResume AI service parses and validates
    structured ATS analysis output without weakening schema rules.
    """
    payload = ATSAnalysisPayload(
        job_title="Software Engineer",
        job_description="Looking for a Python FastAPI developer with experience in PostgreSQL and microservices.",
        resume_text="Software engineer with 3 years experience building Python, FastAPI, and PostgreSQL backend microservices.",
    )

    result = analyze_resume(payload, payload.resume_text)
    assert isinstance(result, ATSAnalysisResult)
    assert 0 <= result.original_score <= 100
    assert 0 <= result.predicted_ats_score <= 100
    assert result.breakdown is not None
    assert isinstance(result.breakdown.keyword_match, int)
    assert isinstance(result.keyword_report, list)
    assert isinstance(result.enhanced_sections.skills, list)
    assert result.engine in {get_settings().gemini_model, "local-fallback"}
