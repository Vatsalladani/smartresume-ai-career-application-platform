import uuid
import pytest
from app.database import SessionLocal
from app.models.user import User
from app.models.master_profile import Profile
from app.models.resume import Resume
from app.services.resume_service import create_resume, update_resume, duplicate_resume


@pytest.fixture
def test_db_user():
    db = SessionLocal()
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        email=f"multi_resume_{unique_id}@example.com",
        password_hash="testhash123",
        full_name="Alex Mercer",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Master Profile
    profile = Profile(
        user_id=user.id,
        headline="Full Stack Engineer",
        summary="Master profile summary with core technical competencies.",
    )
    db.add(profile)
    db.commit()

    yield db, user

    # Cleanup
    db.query(Resume).filter(Resume.user_id == user.id).delete()
    db.query(Profile).filter(Profile.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def test_create_multiple_independent_resumes(test_db_user):
    db, user = test_db_user

    # 1. Create Resume A: Software Engineer - General
    res_a = create_resume(
        db,
        user_id=user.id,
        title="Software Engineer — General",
        status="Draft",
        target_role="Software Engineer",
        parsed_content={
            "summary": "Generalist software engineer building web applications.",
            "skills": ["JavaScript", "React", "Node.js"],
            "projects": [{"title": "WebPortal", "description": "Full-stack dashboard"}]
        }
    )
    assert res_a.id is not None
    assert res_a.status == "Draft"
    assert res_a.title == "Software Engineer — General"

    # 2. Create Resume B: Backend Developer - Targeted
    res_b = create_resume(
        db,
        user_id=user.id,
        title="Backend Developer — Targeted",
        status="Ready",
        target_role="Backend Developer",
        target_company="Razorpay",
        target_location="Bengaluru",
        parsed_content={
            "summary": "High-throughput backend systems architect.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Kafka"],
            "projects": [{"title": "PaymentRouter", "description": "Distributed payments router"}]
        }
    )
    assert res_b.id is not None
    assert res_b.id != res_a.id
    assert res_b.status == "Ready"

    # 3. Edit Resume B and verify Resume A is completely unchanged
    update_resume(
        db,
        res_b,
        title="Backend Developer — Razorpay Special",
        status="Draft",
        parsed_content={
            "summary": "Updated backend summary for payment systems.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis"],
            "projects": [{"title": "PaymentRouter V2", "description": "Sub-millisecond routing"}]
        }
    )
    db.commit()
    db.refresh(res_a)
    db.refresh(res_b)

    # Resume A must remain pristine
    assert res_a.title == "Software Engineer — General"
    assert res_a.parsed_content["skills"] == ["JavaScript", "React", "Node.js"]
    assert res_a.parsed_content["projects"][0]["title"] == "WebPortal"
    assert res_a.status == "Draft"

    # Resume B reflects updates
    assert res_b.title == "Backend Developer — Razorpay Special"
    assert len(res_b.parsed_content["skills"]) == 5
    assert res_b.parsed_content["projects"][0]["title"] == "PaymentRouter V2"


def test_duplicate_resume_independence(test_db_user):
    db, user = test_db_user

    original = create_resume(
        db,
        user_id=user.id,
        title="Marketing Resume",
        status="Ready",
        target_role="Growth Marketer",
        parsed_content={
            "template": "modern_professional",
            "accentColor": "#0d9488",
            "summary": "Growth marketing specialist.",
            "skills": ["SEO", "Content Strategy", "Analytics"]
        }
    )

    # Duplicate
    duplicate = duplicate_resume(db, original, user.id)
    db.commit()
    db.refresh(duplicate)

    assert duplicate.id != original.id
    assert duplicate.title == "Marketing Resume — Copy"
    assert duplicate.status == "Draft"  # Duplicates default to Draft
    assert duplicate.parsed_content["template"] == "modern_professional"
    assert duplicate.parsed_content["accentColor"] == "#0d9488"

    # Modifying duplicate does not modify original
    update_resume(
        db,
        duplicate,
        title="Senior Marketing Lead",
        parsed_content={
            "template": "executive_professional",
            "accentColor": "#7c3aed",
            "summary": "Executive growth leader."
        }
    )
    db.commit()
    db.refresh(original)
    db.refresh(duplicate)

    assert original.title == "Marketing Resume"
    assert original.parsed_content["template"] == "modern_professional"
    assert duplicate.title == "Senior Marketing Lead"
    assert duplicate.parsed_content["template"] == "executive_professional"


def test_resume_archiving_and_filtering(test_db_user):
    db, user = test_db_user

    res = create_resume(db, user_id=user.id, title="Old Intern Resume", status="Draft")
    assert not res.is_archived

    # Archive
    update_resume(db, res, is_archived=True, status="Archived")
    db.commit()
    db.refresh(res)

    assert res.is_archived is True
    assert res.status == "Archived"

    # Active query filters it out
    active_resumes = db.query(Resume).filter(Resume.user_id == user.id, Resume.is_archived.is_(False)).all()
    assert res.id not in [r.id for r in active_resumes]

    # Can unarchive cleanly
    update_resume(db, res, is_archived=False, status="Draft")
    db.commit()
    db.refresh(res)
    assert res.is_archived is False


def test_duplicate_title_numbering_avoids_copy_chains(test_db_user):
    db, user = test_db_user

    base = create_resume(db, user_id=user.id, title="Product Lead", status="Draft")
    db.commit()

    # First duplicate -> "Product Lead — Copy"
    dup1 = duplicate_resume(db, base, user.id)
    db.commit()
    assert dup1.title == "Product Lead — Copy"

    # Second duplicate of base -> "Product Lead — Copy 2"
    dup2 = duplicate_resume(db, base, user.id)
    db.commit()
    assert dup2.title == "Product Lead — Copy 2"

    # Duplicating the duplicate itself should yield "Product Lead — Copy 3", NOT "Product Lead — Copy — Copy"
    dup3 = duplicate_resume(db, dup1, user.id)
    db.commit()
    assert dup3.title == "Product Lead — Copy 3"
    assert "Copy — Copy" not in dup3.title


def test_delete_resume_removes_from_database(test_db_user):
    db, user = test_db_user

    res = create_resume(db, user_id=user.id, title="To Be Deleted", status="Draft")
    db.commit()
    db.refresh(res)
    res_id = res.id

    # Verify exists
    assert db.query(Resume).filter(Resume.id == res_id).first() is not None

    # Delete
    db.delete(res)
    db.commit()

    # Verify completely absent from database
    assert db.query(Resume).filter(Resume.id == res_id).first() is None
    all_user_resumes = db.query(Resume).filter(Resume.user_id == user.id).all()
    assert res_id not in [r.id for r in all_user_resumes]

