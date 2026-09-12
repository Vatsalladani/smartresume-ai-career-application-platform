import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Profile, Experience, Skill, Project, JobPosting, ApplicationVersion
from app.services.auth_service import hash_password

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def setup_user_and_profile():
    db = TestingSessionLocal()
    user = User(
        email="alex.career@test.com",
        password_hash=hash_password("SecurePass123!"),
        full_name="Alex Sharma",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        headline="Senior Backend Engineer | Distributed Systems",
        summary="Experienced backend engineer with 4+ years designing high-availability payment APIs and microservices.",
        target_domain="Software Engineering",
        career_level="MID_SENIOR",
        location="Bengaluru, India",
    )
    db.add(profile)
    db.commit()

    exp = Experience(
        profile_id=profile.id,
        company="Razorpay",
        role_title="Senior Software Engineer",
        description="Architected core payment gateway microservices handling 5,000 transactions/second with 99.99% uptime.",
        start_date="2022-01",
        is_current=True,
        order_index=0,
    )
    db.add(exp)

    sk1 = Skill(profile_id=profile.id, name="Python", proficiency="Expert", category="Backend", evidence_status="VERIFIED", order_index=0)
    sk2 = Skill(profile_id=profile.id, name="PostgreSQL", proficiency="Advanced", category="Database", evidence_status="VERIFIED", order_index=1)
    db.add_all([sk1, sk2])

    proj = Project(
        profile_id=profile.id,
        title="Distributed Event Queue",
        description="Built async event queue using Redis and FastAPI reducing latency by 45%.",
        technologies=["FastAPI", "Redis", "Docker"],
        url="https://github.com/alex/event-queue",
        order_index=0,
    )
    db.add(proj)
    db.commit()

    # Create auth token
    res = client.post("/api/v1/auth/login", json={"email": "alex.career@test.com", "password": "SecurePass123!"})
    token = res.json()["data"]["access_token"]
    user_id = user.id
    db.close()
    return user_id, token


def test_evidence_vault_sync_and_crud():
    user_id, token = setup_user_and_profile()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Sync from profile
    sync_res = client.post("/api/v1/evidence-vault/sync", headers=headers)
    assert sync_res.status_code == 200
    data = sync_res.json()["data"]
    assert data["synced_items_count"] >= 3
    assert data["new_items_created"] >= 3

    # 2. List evidence
    list_res = client.get("/api/v1/evidence-vault", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]
    assert len(items) >= 3

    # 3. Create manual evidence
    create_res = client.post("/api/v1/evidence-vault", headers=headers, json={
        "type": "METRIC",
        "title": "AWS Cloud Optimization",
        "description": "Reduced monthly infrastructure spend by 28% through right-sizing ECS tasks and RDS reserved instances.",
        "context": "Cloud Infrastructure",
        "verification_status": "VERIFIED",
        "confidence": 1.0,
    })
    assert create_res.status_code == 200
    created_item = create_res.json()["data"]
    assert created_item["title"] == "AWS Cloud Optimization"

    # 4. Audit grounding
    audit_res = client.post("/api/v1/evidence-vault/audit", headers=headers, json={
        "statements": [
            "Architected core payment gateway microservices handling 5,000 transactions/second.",
            "Invented quantum blockchain teleportation algorithms in C++."
        ]
    })
    assert audit_res.status_code == 200
    audit_data = audit_res.json()["data"]
    assert audit_data["grounded_count"] >= 1
    assert audit_data["unsupported_count"] >= 1


def test_smartbuild_and_international_rules():
    user_id, token = setup_user_and_profile()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. SmartBuild Init English
    init_res = client.post("/api/v1/smartbuild/init", headers=headers, json={
        "mode": "BUILD_WITH_ME",
        "language": "en",
        "target_country": "India",
    })
    assert init_res.status_code == 200
    assert len(init_res.json()["data"]["questions"]) == 5

    # 2. SmartBuild Init Hindi
    init_hi = client.post("/api/v1/smartbuild/init", headers=headers, json={
        "mode": "BUILD_WITH_ME",
        "language": "hi",
        "target_country": "India",
    })
    assert init_hi.status_code == 200
    assert "रोल" in init_hi.json()["data"]["questions"][0]["question_text"]

    # 3. Synthesize STAR Bullet without fabrication
    star_res = client.post("/api/v1/smartbuild/synthesize-bullet", headers=headers, json={
        "action": "Built real-time transaction reconciliation service",
        "metric": "decreasing audit turnaround by 3 days",
        "tools": "FastAPI and PostgreSQL",
    })
    assert star_res.status_code == 200
    bullet = star_res.json()["data"]["bullet"]
    assert "Built real-time transaction reconciliation service" in bullet
    assert "utilizing FastAPI and PostgreSQL" in bullet
    assert "decreasing audit turnaround by 3 days" in bullet

    # 4. International Rules Check US
    us_rules = client.get("/api/v1/smartbuild/country-rules/US", headers=headers)
    assert us_rules.status_code == 200
    assert us_rules.json()["data"]["photo_allowed"] is False

    # 5. International Rules Check Germany
    de_rules = client.get("/api/v1/smartbuild/country-rules/Germany", headers=headers)
    assert de_rules.status_code == 200
    assert de_rules.json()["data"]["photo_allowed"] is True


def test_application_pack_generation():
    user_id, token = setup_user_and_profile()
    headers = {"Authorization": f"Bearer {token}"}

    db = TestingSessionLocal()
    job = JobPosting(
        user_id=user_id,
        company="Razorpay",
        title="Senior Software Engineer",
        raw_description="Senior Software Engineer to build resilient distributed payment pipelines with Python and PostgreSQL.",
    )
    db.add(job)
    db.commit()

    ver = ApplicationVersion(
        job_id=job.id,
        version_number=1,
        template_name="classic_ats",
        ats_score=85,
        content_json={"summary": "Senior engineer with payment systems experience."},
    )
    db.add(ver)
    db.commit()
    ver_id = ver.id
    job_id = job.id
    db.close()

    # Generate 13-asset Application Pack
    pack_res = client.post("/api/v1/application-pack/generate", headers=headers, json={
        "version_id": ver_id,
        "job_id": job_id,
        "tone": "professional",
        "target_geography": "India",
    })
    assert pack_res.status_code == 200
    pack = pack_res.json()["data"]

    assert "cover_letter" in pack
    assert "Senior Software Engineer" in pack["cover_letter"]
    assert "Razorpay" in pack["cover_letter"]

    assert "recruiter_email" in pack
    assert "gmail_url" in pack["recruiter_email"]
    assert "mail.google.com" in pack["recruiter_email"]["gmail_url"]

    assert "application_answers" in pack
    assert len(pack["application_answers"]) >= 3

    assert "application_checklist" in pack
    assert "follow_up_strategy" in pack
    assert "interview_prep_brief" in pack
    assert "risk_and_honesty_check" in pack


def test_ai_interview_copilot_flow():
    user_id, token = setup_user_and_profile()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start Session
    start_res = client.post("/api/v1/interview/sessions", headers=headers, json={
        "target_role": "Senior Backend Engineer",
        "target_company": "Razorpay",
        "session_mode": "TEXT",
    })
    assert start_res.status_code == 200
    session = start_res.json()["data"]
    session_id = session["id"]
    assert session["target_role"] == "Senior Backend Engineer"
    assert len(session["messages"]) == 1
    assert session["messages"][0]["sender"] == "AI"

    # 2. Submit Candidate Turn with STAR response
    turn_res = client.post(f"/api/v1/interview/sessions/{session_id}/turns", headers=headers, json={
        "message_text": "I led the migration from our legacy monolithic MySQL database to PostgreSQL. I designed the schema and automated table replication using Docker, resulting in a 40% reduction in query latency and zero downtime for 100k users.",
    })
    assert turn_res.status_code == 200
    turn_data = turn_res.json()["data"]
    assert "user_message" in turn_data
    assert "ai_response" in turn_data
    assert turn_data["turn_feedback"]["metrics_detected"] is True

    # 3. Complete and Evaluate
    comp_res = client.post(f"/api/v1/interview/sessions/{session_id}/complete", headers=headers)
    assert comp_res.status_code == 200
    eval_data = comp_res.json()["data"]
    assert "readiness_level" in eval_data
    assert len(eval_data["strong_areas"]) > 0
    assert len(eval_data["resume_claims_to_defend"]) > 0


def test_job_radar_and_career_insights():
    user_id, token = setup_user_and_profile()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Job Radar Search
    radar_res = client.get("/api/v1/job-radar?query=Backend", headers=headers)
    assert radar_res.status_code == 200
    radar_data = radar_res.json()["data"]
    assert radar_data["total_found"] >= 1
    assert len(radar_data["listings"]) >= 1
    first = radar_data["listings"][0]
    assert first["match_category"] in ("STRONG_MATCH", "REACH", "STRETCH", "BACKUP")

    # 2. Career Insights
    insights_res = client.get("/api/v1/career-insights", headers=headers)
    assert insights_res.status_code == 200
    insights = insights_res.json()["data"]
    assert insights["target_domain"] == "Software Engineering"
    assert len(insights["skills_in_high_demand"]) >= 4
    assert "career_pathway" in insights
    assert "target_level" in insights["career_pathway"]


def test_notifications_and_pro_trial_activation():
    user_id, token = setup_user_and_profile()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start 7-Day Pro Trial (₹0)
    trial_res = client.post("/api/v1/payments/start-trial", headers=headers)
    assert trial_res.status_code == 200
    trial_data = trial_res.json()["data"]
    assert trial_data["is_trial"] is True
    assert trial_data["days_remaining"] == 7

    # 2. Ensure Single-use Trial Guard
    repeat_res = client.post("/api/v1/payments/start-trial", headers=headers)
    assert repeat_res.status_code == 200
    assert repeat_res.json()["data"]["is_trial"] is False
    assert repeat_res.json()["data"]["trial_used"] is True

    # 3. Check Notifications
    notif_res = client.get("/api/v1/notifications", headers=headers)
    assert notif_res.status_code == 200
    notif_data = notif_res.json()["data"]
    assert len(notif_data["notifications"]) >= 1
    first_notif = notif_data["notifications"][0]
    assert "Trial" in first_notif["title"]

    # 4. Mark Read
    read_res = client.post(f"/api/v1/notifications/{first_notif['id']}/read", headers=headers)
    assert read_res.status_code == 200
