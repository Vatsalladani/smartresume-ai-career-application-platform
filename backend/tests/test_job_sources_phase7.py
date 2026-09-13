import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Ensure all SQLAlchemy models are registered
from app.database import Base
from app.models.user import User
from app.models.master_profile import Profile, Skill
from app.models.job_fit import JobPosting, JobRequirement
from app.services.job_radar_service import search_job_radar
from app.services.company_verification_service import verify_company
from app.schemas.company_verification import CompanyVerificationRequest


@pytest.fixture
def test_db_session():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def test_job_radar_seed_isolation(test_db_session):
    # Setup test user and profile
    user = User(
        email="radar_tester@example.com",
        password_hash="hashed_test_password",
        full_name="Radar Tester",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()

    profile = Profile(user_id=user.id, headline="Backend Python Architect")
    test_db_session.add(profile)
    test_db_session.commit()

    skill = Skill(profile_id=profile.id, name="Python", proficiency="EXPERT")
    test_db_session.add(skill)
    test_db_session.commit()

    # 1. Search with include_seeds=True (default)
    res_with_seeds = search_job_radar(
        db=test_db_session,
        user_id=user.id,
        query="Backend",
        include_seeds=True,
    )
    assert res_with_seeds.total_found >= 1
    assert res_with_seeds.includes_demo_seeds is True
    assert res_with_seeds.provider_status == "CONFIGURATION_PENDING"
    assert any(item.is_seed is True for item in res_with_seeds.listings)
    assert any(item.source == "Curated Tech Demo Seeds" for item in res_with_seeds.listings)

    # 2. Search with include_seeds=False (Seeds completely isolated)
    res_without_seeds = search_job_radar(
        db=test_db_session,
        user_id=user.id,
        query="Backend",
        include_seeds=False,
    )
    assert res_without_seeds.total_found == 0
    assert res_without_seeds.includes_demo_seeds is False
    assert len(res_without_seeds.listings) == 0

    # 3. Add real user saved job posting to database
    db_job = JobPosting(
        user_id=user.id,
        title="Senior Python Platform Lead",
        company="Fintech Co",
        location="Bengaluru, India",
        raw_description="Design and build high-throughput distributed microservices in Python and FastAPI.",
        target_domain="Software Engineering",
    )
    test_db_session.add(db_job)
    test_db_session.commit()

    # Search again with include_seeds=False -> Only real DB job returned
    res_db_only = search_job_radar(
        db=test_db_session,
        user_id=user.id,
        query="Platform",
        include_seeds=False,
    )
    assert res_db_only.total_found == 1
    listing = res_db_only.listings[0]
    assert listing.id == f"db-{db_job.id}"
    assert listing.title == "Senior Python Platform Lead"
    assert listing.is_seed is False
    assert listing.source == "Saved Job Postings"


def test_company_verification_known_vs_unknown():
    # Known organization
    res_known = verify_company(
        CompanyVerificationRequest(company_name="Razorpay", company_url="https://razorpay.com")
    )
    assert res_known.verification_status == "VERIFIED"
    assert res_known.confidence in ("HIGH", "MEDIUM")
    assert "razorpay.com" in res_known.official_domain

    # Unknown organization without official records or domain
    res_unknown = verify_company(
        CompanyVerificationRequest(company_name="Nonexistent Phantom Startup")
    )
    assert res_unknown.verification_status == "COULD_NOT_VERIFY"
    assert res_unknown.confidence == "LOW"
