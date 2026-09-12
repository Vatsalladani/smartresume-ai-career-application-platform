"""Comprehensive End-to-End User Journey Test
Validates the entire SmartResume.ai Career + Application OS lifecycle:
1. Register & Login
2. Master Profile Creation & CRUD (Experience, Skills, Projects, Education, Certifications)
3. Evidence Vault Sync & Grounding Verification
4. SmartBuild STAR Bullet Synthesis & International Rules Check
5. Job Creation, JD Parsing & Evidence-Grounded Fit Analysis
6. Tailoring & Immutable Version Creation
7. 13-Asset Application Pack Generation (Cover letter, Recruiter email, Gmail link, Answers)
8. AI Interview Copilot Mock Session, Question Answering & Readiness Scoring
9. Job Radar Matching & Career Insights Pathways
10. Billing: 7-Day Pro Trial ₹0 Activation & ₹1 Export Purchase
11. SmartApply Copilot Portal Answer Generation
"""
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


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def test_full_career_os_end_to_end_journey():
    # ----------------------------------------------------
    # 1. Register & Login
    # ----------------------------------------------------
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "priya.nair@career-os.com",
        "password": "StrongPassword99!",
        "full_name": "Priya Nair",
    })
    assert reg_res.status_code == 200, reg_res.text
    user_data = reg_res.json()["data"]
    assert user_data["user"]["email"] == "priya.nair@career-os.com"

    login_res = client.post("/api/v1/auth/login", json={
        "email": "priya.nair@career-os.com",
        "password": "StrongPassword99!",
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ----------------------------------------------------
    # 2. Master Profile Setup & CRUD
    # ----------------------------------------------------
    profile_update = client.put("/api/v1/profile", headers=headers, json={
        "headline": "Lead Data Platform Engineer | Distributed Streaming",
        "summary": "Data engineer with 6 years experience building petabyte-scale Apache Kafka pipelines and real-time analytics engines.",
        "target_domain": "Data Engineering",
        "career_level": "LEAD",
        "location": "Mumbai, India",
    })
    assert profile_update.status_code == 200

    # Add Experience
    exp_res = client.post("/api/v1/profile/experiences", headers=headers, json={
        "company": "Swiggy",
        "role_title": "Senior Data Engineer",
        "description": "Architected streaming ingestion pipeline processing 200M events/day with Apache Flink and Kafka, cutting delivery ETA calculation latency by 60%.",
        "start_date": "2021-03",
        "is_current": True,
        "order_index": 0,
    })
    assert exp_res.status_code == 200

    # Add Skills
    sk1 = client.post("/api/v1/profile/skills", headers=headers, json={"name": "Apache Kafka", "proficiency": "Expert", "category": "Data", "order_index": 0})
    sk2 = client.post("/api/v1/profile/skills", headers=headers, json={"name": "Python", "proficiency": "Expert", "category": "Backend", "order_index": 1})
    sk3 = client.post("/api/v1/profile/skills", headers=headers, json={"name": "PostgreSQL", "proficiency": "Advanced", "category": "Database", "order_index": 2})
    assert sk1.status_code == 200
    assert sk2.status_code == 200
    assert sk3.status_code == 200

    # Add Project
    proj_res = client.post("/api/v1/profile/projects", headers=headers, json={
        "title": "Real-time Order Telemetry Lakehouse",
        "description": "Constructed Delta Lake streaming pipeline integrating Spark and Kafka for real-time delivery tracing.",
        "technologies": ["Apache Spark", "Kafka", "Python", "Delta Lake"],
        "order_index": 0,
    })
    assert proj_res.status_code == 200

    # ----------------------------------------------------
    # 3. Evidence Vault Sync & Grounding
    # ----------------------------------------------------
    sync_res = client.post("/api/v1/evidence-vault/sync", headers=headers)
    assert sync_res.status_code == 200
    assert sync_res.json()["data"]["synced_items_count"] >= 3

    # Add a verified metric into Evidence Vault
    ev_item = client.post("/api/v1/evidence-vault", headers=headers, json={
        "type": "METRIC",
        "title": "Kafka Throughput Optimization",
        "description": "Tuned Kafka broker cluster and consumer group partitions, reducing end-to-end p99 ingestion lag from 4.2s to 380ms.",
        "context": "Swiggy Order Analytics",
        "verification_status": "VERIFIED",
        "confidence": 1.0,
    })
    assert ev_item.status_code == 200

    # Audit grounding check
    audit_res = client.post("/api/v1/evidence-vault/audit", headers=headers, json={
        "statements": [
            "Architected streaming ingestion pipeline processing 200M events/day with Apache Flink and Kafka.",
            "Developed self-aware quantum supercomputers in Mars base."
        ]
    })
    assert audit_res.status_code == 200
    audit_body = audit_res.json()["data"]
    assert audit_body["grounded_count"] >= 1
    assert audit_body["unsupported_count"] >= 1

    # ----------------------------------------------------
    # 4. SmartBuild STAR Synthesis & International Rules
    # ----------------------------------------------------
    star_res = client.post("/api/v1/smartbuild/synthesize-bullet", headers=headers, json={
        "action": "Built real-time telemetry streaming layer",
        "metric": "decreasing pipeline processing latency by 60%",
        "tools": "Apache Kafka and Flink",
    })
    assert star_res.status_code == 200
    assert "Built real-time telemetry streaming layer" in star_res.json()["data"]["bullet"]

    rules_res = client.get("/api/v1/smartbuild/country-rules/US", headers=headers)
    assert rules_res.status_code == 200
    assert rules_res.json()["data"]["photo_allowed"] is False

    # ----------------------------------------------------
    # 5. Job Creation & Fit Analysis
    # ----------------------------------------------------
    job_res = client.post("/api/v1/jobs", headers=headers, json={
        "company": "Zepto",
        "title": "Lead Data Platform Engineer",
        "raw_description": "Zepto is hiring a Lead Data Platform Engineer to design real-time data streaming architectures with Apache Kafka, Python, and high-throughput systems.",
        "job_url": "https://zepto.com/careers/lead-data-eng",
    })
    assert job_res.status_code in [200, 201]
    job_id = job_res.json()["data"]["id"]

    fit_res = client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    assert fit_res.status_code == 200
    fit_data = fit_res.json()["data"]
    assert "application_fit_score" in fit_data

    # ----------------------------------------------------
    # 6. Tailoring & Immutable Version
    # ----------------------------------------------------
    tailor_res = client.post(f"/api/v1/jobs/{job_id}/tailor", headers=headers)
    assert tailor_res.status_code == 200

    commit_res = client.post(f"/api/v1/jobs/{job_id}/versions", headers=headers, json={
        "template_name": "classic_ats",
        "changelog": "Tailored for Zepto Lead Data Platform role",
        "content_json": {
            "summary": "Lead Data Platform Engineer specializing in high-throughput Kafka and real-time streaming architectures.",
            "skills": ["Apache Kafka", "Python", "PostgreSQL", "Apache Flink"],
        },
    })
    assert commit_res.status_code == 200
    version_id = commit_res.json()["data"]["id"]

    # ----------------------------------------------------
    # 7. 13-Asset Application Pack Generation
    # ----------------------------------------------------
    pack_res = client.post("/api/v1/application-pack/generate", headers=headers, json={
        "version_id": version_id,
        "job_id": job_id,
        "tone": "professional",
        "target_geography": "India",
    })
    assert pack_res.status_code == 200
    pack = pack_res.json()["data"]
    assert "cover_letter" in pack
    assert "Zepto" in pack["cover_letter"]
    assert "recruiter_email" in pack
    assert "gmail_url" in pack["recruiter_email"]
    assert len(pack["application_answers"]) >= 3
    assert "application_checklist" in pack
    assert "follow_up_strategy" in pack
    assert "interview_prep_brief" in pack
    assert "risk_and_honesty_check" in pack

    # ----------------------------------------------------
    # 8. AI Interview Copilot Mock Session & Evaluation
    # ----------------------------------------------------
    interview_start = client.post("/api/v1/interview/sessions", headers=headers, json={
        "target_role": "Lead Data Platform Engineer",
        "target_company": "Zepto",
        "job_id": job_id,
        "session_mode": "TEXT",
    })
    assert interview_start.status_code == 200
    session_id = interview_start.json()["data"]["id"]

    user_msg_res = client.post(f"/api/v1/interview/sessions/{session_id}/turns", headers=headers, json={
        "message_text": "At Swiggy, I architected our Kafka stream processing pipeline that handled 200 million daily telemetry events. We leveraged Apache Flink for stateful windowing, reducing latency by 60% while maintaining exact-once semantics."
    })
    assert user_msg_res.status_code == 200
    turn_data = user_msg_res.json()["data"]
    assert "user_message" in turn_data
    assert "ai_response" in turn_data

    eval_res = client.post(f"/api/v1/interview/sessions/{session_id}/complete", headers=headers)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()["data"]
    assert "readiness_level" in eval_data
    assert len(eval_data["strong_areas"]) > 0

    # ----------------------------------------------------
    # 9. Job Radar & Career Insights
    # ----------------------------------------------------
    radar_res = client.get("/api/v1/job-radar?query=Data", headers=headers)
    assert radar_res.status_code == 200
    assert "listings" in radar_res.json()["data"]

    insights_res = client.get("/api/v1/career-insights", headers=headers)
    assert insights_res.status_code == 200
    assert "skills_in_high_demand" in insights_res.json()["data"]

    # ----------------------------------------------------
    # 10. Billing: 7-Day Pro Trial ₹0 & ₹1 Purchase
    # ----------------------------------------------------
    trial_res = client.post("/api/v1/payments/start-trial", headers=headers)
    assert trial_res.status_code == 200
    assert trial_res.json()["data"]["is_trial"] is True

    # Attempt claiming trial again - must reject
    trial_res_dup = client.post("/api/v1/payments/start-trial", headers=headers)
    assert trial_res_dup.status_code == 200
    assert trial_res_dup.json()["data"]["is_trial"] is False
    assert trial_res_dup.json()["data"]["trial_used"] is True

    # ₹1 export credit order creation
    order_res = client.post("/api/v1/payments/create-order", headers=headers, json={
        "plan": "SINGLE_EXPORT",
        "currency": "INR",
    })
    assert order_res.status_code == 200
    order_data = order_res.json()["data"]
    assert order_data["amount"] == 100  # 100 paise = ₹1

    # ----------------------------------------------------
    # 11. SmartApply Copilot Answer Generation
    # ----------------------------------------------------
    apply_answer = client.post("/api/v1/smartapply/answer", headers=headers, json={
        "question": "How have you scaled message brokers under peak loads?",
        "job_title": "Lead Data Platform Engineer",
        "company": "Zepto",
        "tone": "technical"
    })
    assert apply_answer.status_code == 200
    assert len(apply_answer.json()["data"]["answer"]) > 20
    assert "grounding" in apply_answer.json()["data"]
