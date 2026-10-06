import pytest
from app.services import international_rules
from app.services.export_service import generate_professional_filename
from app.models.resume import Resume
from app.models.master_profile import Profile
from app.services.resume_service import create_resume, update_resume, duplicate_resume
from app.services.profile_service import get_or_create_profile, update_profile
from app.schemas.master_profile import ProfileUpdate


def test_market_presets_coverage():
    """Verify that at least 12 international market presets exist with required guidance."""
    expected_markets = ["GLOBAL", "US", "CA", "UK", "AU", "NZ", "DE", "EU", "SG", "AE", "SA", "IN"]
    presets = international_rules.get_all_market_presets()
    preset_codes = [p["code"] for p in presets]

    for code in expected_markets:
        assert code in preset_codes
        rules = international_rules.get_country_guidelines(code)
        assert "terminology" in rules
        assert "photo_guidance" in rules
        assert "recommended_pages" in rules
        assert "spelling" in rules
        assert "education_guidance" in rules
        assert "personal_info_guidance" in rules
        assert "date_format_recommended" in rules


def test_detect_market_from_location():
    """Test smart detection of market guidance from job location without forcing."""
    cases = [
        ("Toronto, ON, Canada", "CA", "Canada"),
        ("New York, NY, USA", "US", "United States"),
        ("London, England, UK", "UK", "United Kingdom"),
        ("Berlin, Germany", "DE", "Germany (DACH)"),
        ("Sydney, NSW, Australia", "AU", "Australia"),
        ("Auckland, New Zealand", "NZ", "New Zealand"),
        ("Singapore", "SG", "Singapore"),
        ("Dubai, UAE", "AE", "United Arab Emirates"),
        ("Riyadh, Saudi Arabia", "SA", "Saudi Arabia / GCC"),
        ("Bengaluru, India", "IN", "India"),
        ("Amsterdam, Netherlands", "EU", "European Union / Europe"),
        ("Remote / Worldwide", "GLOBAL", "Global / International"),
    ]

    for loc, exp_code, exp_name in cases:
        res = international_rules.detect_market_from_location(loc)
        assert res["market_code"] == exp_code
        assert exp_name in res["market_name"]


def test_template_recommendations():
    """Test market & role aware ATS template recommendation."""
    # Tech role in US
    tpl_us_tech = international_rules.recommend_template_for_market("US", role="Software Engineer", career_level="MID")
    assert tpl_us_tech in ("classic_ats", "technical_ats")

    # Academic in EU
    tpl_eu_acad = international_rules.recommend_template_for_market("EU", role="Postdoctoral Researcher", career_level="SENIOR")
    assert tpl_eu_acad == "academic_research"

    # Executive in UAE
    tpl_ae_exec = international_rules.recommend_template_for_market("AE", role="Chief Technology Officer", career_level="EXECUTIVE")
    assert tpl_ae_exec == "executive_professional"


def test_professional_filename_generation():
    """Test standard human-readable professional file names for exports."""
    # 1. Role-targeted resume
    fn1 = generate_professional_filename(
        user_name="Vatsal Ladani",
        target_role="Backend Developer",
        document_purpose="Professional Resume",
        file_format="pdf",
    )
    assert fn1 == "Vatsal_Ladani_Backend_Developer.pdf"

    # 2. General CV
    fn2 = generate_professional_filename(
        user_name="Vatsal Ladani",
        target_role=None,
        document_purpose="Professional CV",
        file_format="docx",
    )
    assert fn2 == "Vatsal_Ladani_CV.docx"

    # 3. Academic CV
    fn3 = generate_professional_filename(
        user_name="Dr. Jane Smith",
        target_role=None,
        document_purpose="Academic CV",
        file_format="pdf",
    )
    assert fn3 == "Dr_Jane_Smith_Academic_CV.pdf"

    # 4. Standard default
    fn4 = generate_professional_filename(
        user_name="John Doe",
        target_role="",
        document_purpose="Professional Resume",
        file_format="pdf",
    )
    assert fn4 == "John_Doe_Resume.pdf"


import uuid
from app.database import SessionLocal
from app.models.user import User


@pytest.fixture
def test_db_user():
    db = SessionLocal()
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        email=f"intl_workspace_{unique_id}@example.com",
        password_hash="testhash123",
        full_name="Vatsal Ladani",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    yield db, user

    # Cleanup
    db.query(Resume).filter(Resume.user_id == user.id).delete()
    db.query(Profile).filter(Profile.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def test_multi_resume_with_market_and_purpose(test_db_user):
    """Test that resumes persist target_market, document_purpose, and ats_mode independently."""
    db_session, test_user = test_db_user
    r1 = create_resume(
        db_session,
        user_id=test_user.id,
        title="US Tech Resume",
        target_market="US",
        document_purpose="Professional Resume",
        ats_mode="ATS-Safe",
        target_role="Full Stack Engineer",
        raw_text="Experienced engineer with Python and React.",
    )
    assert r1.target_market == "US"
    assert r1.document_purpose == "Professional Resume"
    assert r1.ats_mode == "ATS-Safe"

    r2 = create_resume(
        db_session,
        user_id=test_user.id,
        title="UK Academic CV",
        target_market="UK",
        document_purpose="Academic CV",
        ats_mode="Balanced",
        target_role="Research Associate",
        raw_text="Published papers in distributed computing.",
    )
    assert r2.target_market == "UK"
    assert r2.document_purpose == "Academic CV"
    assert r2.ats_mode == "Balanced"

    # Duplicate r1 and verify independent properties
    r1_copy = duplicate_resume(db_session, r1, test_user.id, new_title="US Tech Resume — Tailored")
    assert r1_copy.target_market == "US"
    assert r1_copy.document_purpose == "Professional Resume"
    assert r1_copy.ats_mode == "ATS-Safe"
    assert r1_copy.title == "US Tech Resume — Tailored"

    # Modify r1_copy to Canada without modifying r1
    update_resume(db_session, r1_copy, target_market="CA", ats_mode="Visual")
    db_session.refresh(r1)
    db_session.refresh(r1_copy)

    assert r1.target_market == "US"
    assert r1.ats_mode == "ATS-Safe"
    assert r1_copy.target_market == "CA"
    assert r1_copy.ats_mode == "Visual"


def test_profile_career_status_and_market(test_db_user):
    """Test updating career status (e.g. Employed) and default market on user profile."""
    db_session, test_user = test_db_user
    prof = get_or_create_profile(db_session, test_user.id)
    assert prof.career_status == "Job Searching"
    assert prof.target_market == "Global"

    update_profile(
        db_session,
        test_user.id,
        ProfileUpdate(
            career_status="Employed",
            target_market="US",
            headline="Senior Backend Engineer at Tech Corp",
        ),
    )
    db_session.refresh(prof)
    assert prof.career_status == "Employed"
    assert prof.target_market == "US"
    assert prof.headline == "Senior Backend Engineer at Tech Corp"
