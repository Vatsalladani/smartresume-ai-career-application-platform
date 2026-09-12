"""Unit tests for Company Verification Service & Endpoints
"""
import pytest
from app.schemas.company_verification import CompanyVerificationRequest
from app.services.company_verification_service import verify_company, get_cached_verification


def test_known_company_verification():
    req = CompanyVerificationRequest(company_name="Microsoft")
    result = verify_company(req)
    assert result.verification_status == "VERIFIED"
    assert result.confidence == "HIGH"
    assert result.official_domain == "microsoft.com"
    assert len(result.sources) > 0
    assert "Official company website" in result.sources


def test_unknown_company_without_domain():
    req = CompanyVerificationRequest(company_name="Nonexistent Phantom Startup")
    result = verify_company(req)
    assert result.verification_status == "COULD_NOT_VERIFY"
    assert result.confidence == "LOW"
    # Must NOT claim company does not exist
    assert "does not exist" not in result.summary.lower()
    assert "Add the company's official website" in result.summary


def test_startup_with_valid_domain():
    req = CompanyVerificationRequest(
        company_name="Nexara Robotics",
        company_url="https://nexara-robotics.io",
        job_url="https://nexara-robotics.io/careers/engineer",
    )
    result = verify_company(req)
    assert result.verification_status in ("VERIFIED", "LIKELY_VERIFIED")
    assert result.confidence in ("HIGH", "MEDIUM")
    assert result.official_domain == "nexara-robotics.io"


def test_recruiter_email_free_provider_warning():
    req = CompanyVerificationRequest(
        company_name="Acme Systems",
        company_url="https://acmesystems.com",
        recruiter_email="hr_recruiter@gmail.com",
    )
    result = verify_company(req)
    assert any("does not use the company's domain" in w for w in result.warnings)


def test_job_url_domain_mismatch_warning():
    req = CompanyVerificationRequest(
        company_name="Google",
        company_url="https://google.com",
        job_url="https://some-unrelated-site.com/jobs/123",
    )
    result = verify_company(req)
    assert any("does not directly match" in w for w in result.warnings)


def test_suspicious_language_flag():
    req = CompanyVerificationRequest(
        company_name="Quick Cash Corp",
        job_description="Please wire transfer money for home office equipment before your interview.",
    )
    result = verify_company(req)
    assert result.verification_status == "SUSPICIOUS"
    assert result.confidence == "CAUTION"
    assert any("suspicious recruiting language" in w.lower() for w in result.warnings)


def test_verification_caching():
    req = CompanyVerificationRequest(company_name="Razorpay")
    res1 = verify_company(req)
    cached = get_cached_verification("Razorpay")
    assert cached is not None
    assert cached.company_name == res1.company_name
