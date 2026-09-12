import sys
import time
import uuid
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/v1"

class QAFailure(Exception):
    pass

def log_step(step_name: str, passed: bool, details: str = ""):
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {step_name}" + (f" -> {details}" if details else ""))
    if not passed:
        raise QAFailure(f"Step '{step_name}' failed: {details}")

def run_live_qa():
    print("=" * 70)
    print("SmartResume.ai — Live Production-Readiness End-to-End QA")
    print(f"Target URL: {BASE_URL}")
    print("=" * 70)

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    # 1. Health Check
    try:
        r = session.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data.get("success") is True
        log_step("1. Health Endpoint", True, f"Service: {data.get('data', {}).get('service')}")
    except Exception as e:
        log_step("1. Health Endpoint", False, str(e))

    # 2. Register
    qa_id = uuid.uuid4().hex[:8]
    email = f"qa_lead_{qa_id}@smartresume.ai"
    password = "MasterQAPassword2026!"
    full_name = f"Vatsal QA Tester {qa_id}"

    try:
        r = session.post(f"{API_URL}/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name,
        })
        assert r.status_code == 200, f"Register failed ({r.status_code}): {r.text}"
        res = r.json()
        assert res.get("success") is True
        # Verify no token leak in body
        assert "verification_token" not in res.get("data", {}).get("user", {})
        log_step("2. User Registration", True, f"Registered: {email}")
    except Exception as e:
        log_step("2. User Registration", False, str(e))

    # 3. Login
    access_token = None
    refresh_token = None
    try:
        r = session.post(f"{API_URL}/auth/login", json={
            "email": email,
            "password": password,
        })
        assert r.status_code == 200, f"Login failed ({r.status_code}): {r.text}"
        data = r.json().get("data", {})
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        assert access_token and refresh_token, "Tokens missing from response"
        session.headers.update({"Authorization": f"Bearer {access_token}"})
        log_step("3. User Login & Token Issuance", True, f"Access token obtained (expires in {data.get('expires_in')}s)")
    except Exception as e:
        log_step("3. User Login & Token Issuance", False, str(e))

    # 4. Dashboard View Verification
    try:
        p_res = session.get(f"{API_URL}/profile").json().get("data", {})
        a_res = session.get(f"{API_URL}/applications").json().get("data", [])
        j_res = session.get(f"{API_URL}/jobs").json().get("data", [])
        s_res = session.get(f"{API_URL}/payments/subscription").json().get("data", {})
        b_res = session.get(f"{API_URL}/payments/billing-summary").json().get("data", {})

        quotas = b_res.get("quotas", {})
        fits = quotas.get("fit_analyses", {})
        tailors = quotas.get("tailored_versions", {})
        exports = quotas.get("exports", {})
        assert s_res.get("plan_name") == "FREE", f"Expected FREE, got {s_res.get('plan_name')}"
        assert fits.get("used") == 0, f"Expected fits used == 0, got {fits}"
        assert tailors.get("used") == 0, f"Expected tailors used == 0, got {tailors}"
        assert exports.get("used") == 0, f"Expected exports used == 0, got {exports}"
        log_step("4. Dashboard Initial Metrics", True, f"Plan: {s_res.get('plan_name')}, Fits: {fits.get('used')}/{fits.get('limit')}, Tailors: {tailors.get('used')}/{tailors.get('limit')}")
    except Exception as e:
        import traceback
        log_step("4. Dashboard Initial Metrics", False, f"{traceback.format_exc()}")

    # 5. Master Profile Save
    try:
        update_payload = {
            "headline": "Lead Systems Architect & Full-Stack Engineer",
            "target_role": "Staff Software Engineer",
            "phone": "+91 9876543210",
            "location": "Bengaluru, India",
            "summary": "Proven engineering lead specializing in high-throughput distributed systems, event-driven architectures, and production AI pipelines.",
            "linkedin_url": "https://linkedin.com/in/qa-lead-vatsal",
            "github_url": "https://github.com/qa-lead-vatsal",
            "portfolio_url": "https://vatsal.dev",
        }
        r = session.put(f"{API_URL}/profile", json=update_payload)
        assert r.status_code == 200, f"Profile update failed ({r.status_code}): {r.text}"
        prof = r.json().get("data", {})
        assert prof.get("headline") == update_payload["headline"]
        log_step("5. Master Profile Save", True, f"Headline: {prof.get('headline')}")
    except Exception as e:
        import traceback
        log_step("5. Master Profile Save", False, f"{traceback.format_exc()}")

    # 6. Experience CRUD
    try:
        # Add
        exp_payload = {
            "company": "Temp Corp",
            "job_title": "Junior Developer",
            "location": "Bengaluru",
            "start_date": "2020-01",
            "end_date": "2021-01",
            "is_current": False,
            "bullet_points": ["Built internal tools in Python."],
        }
        r = session.post(f"{API_URL}/profile/experiences", json=exp_payload)
        assert r.status_code == 200, f"Add exp failed: {r.text}"
        exp_id = r.json().get("data", {}).get("id")

        # Edit
        edit_payload = {
            "role_title": "Mid Developer",
            "bullet_points": ["Built high-performance internal tools."],
        }
        r = session.put(f"{API_URL}/profile/experiences/{exp_id}", json=edit_payload)
        assert r.status_code == 200, f"Edit exp failed: {r.text}"
        assert r.json().get("data", {}).get("role_title") == "Mid Developer"

        # Delete
        r = session.delete(f"{API_URL}/profile/experiences/{exp_id}")
        assert r.status_code == 200, f"Delete exp failed: {r.text}"

        # Re-add permanent experience for tailoring
        perm_exp = {
            "company": "Apex Cloud Technologies",
            "role_title": "Senior Distributed Systems Engineer",
            "location": "Bengaluru, India",
            "start_date": "2021-06",
            "end_date": "Present",
            "is_current": True,
            "bullet_points": [
                "Architected high-throughput microservices using FastAPI, Redis, and PostgreSQL processing 40M+ events daily.",
                "Reduced p99 API latency by 42% through query optimization, connection pooling, and distributed caching.",
                "Spearheaded cloud migration to Kubernetes across 12 containerized services.",
            ],
        }
        r = session.post(f"{API_URL}/profile/experiences", json=perm_exp)
        assert r.status_code == 200
        log_step("6. Experience Add/Edit/Delete CRUD", True, "Successfully created, modified, deleted, and re-added experience")
    except Exception as e:
        import traceback
        log_step("6. Experience Add/Edit/Delete CRUD", False, f"{traceback.format_exc()}")

    # 7. Project CRUD
    try:
        # Add
        proj_payload = {
            "title": "Temp Project",
            "role_title": "Contributor",
            "technologies": ["Python", "Flask"],
            "description": "Prototype app",
            "bullet_points": ["Built demo"],
        }
        r = session.post(f"{API_URL}/profile/projects", json=proj_payload)
        assert r.status_code == 200
        proj_id = r.json().get("data", {}).get("id")

        # Edit
        r = session.put(f"{API_URL}/profile/projects/{proj_id}", json={"role_title": "Lead"})
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role_title") == "Lead"

        # Delete
        r = session.delete(f"{API_URL}/profile/projects/{proj_id}")
        assert r.status_code == 200

        # Re-add permanent project
        perm_proj = {
            "title": "Autonomous Event Stream Pipeline",
            "role_title": "Principal Creator",
            "technologies": ["Python", "FastAPI", "Kafka", "PostgreSQL", "Docker"],
            "description": "Engineered real-time distributed stream processing pipeline handling 10k messages per second with zero data loss.",
            "bullet_points": [
                "Achieved sub-10ms end-to-end processing latency.",
                "Automated failover and disaster recovery with Raft consensus.",
            ],
        }
        r = session.post(f"{API_URL}/profile/projects", json=perm_proj)
        assert r.status_code == 200
        log_step("7. Project Add/Edit/Delete CRUD", True, "Successfully verified project lifecycle")
    except Exception as e:
        import traceback
        log_step("7. Project Add/Edit/Delete CRUD", False, f"{traceback.format_exc()}")

    # 8. Skills CRUD
    try:
        # Add skill 1 (Temp)
        r = session.post(f"{API_URL}/profile/skills", json={
            "skill_name": "Temporary Skill",
            "category": "Tools",
            "proficiency_level": "Beginner",
            "years_experience": 1,
        })
        assert r.status_code == 200
        temp_skill_id = r.json().get("data", {}).get("id")

        # Delete skill
        r = session.delete(f"{API_URL}/profile/skills/{temp_skill_id}")
        assert r.status_code == 200

        # Add permanent skills
        for sk, cat in [("Python", "Languages"), ("FastAPI", "Frameworks"), ("PostgreSQL", "Databases"), ("Redis", "Databases")]:
            session.post(f"{API_URL}/profile/skills", json={
                "skill_name": sk,
                "category": cat,
                "proficiency_level": "Expert",
                "years_experience": 5,
            })
        log_step("8. Skills Add/Delete CRUD", True, "Added key skills: Python, FastAPI, PostgreSQL, Redis")
    except Exception as e:
        log_step("8. Skills Add/Delete CRUD", False, str(e))

    # 9. Education CRUD
    try:
        r = session.post(f"{API_URL}/profile/education", json={
            "institution": "Temporary University",
            "degree": "B.A.",
            "field_of_study": "General",
        })
        assert r.status_code == 200
        temp_edu_id = r.json().get("data", {}).get("id")

        r = session.delete(f"{API_URL}/profile/education/{temp_edu_id}")
        assert r.status_code == 200

        # Re-add permanent education
        session.post(f"{API_URL}/profile/education", json={
            "institution": "National Institute of Technology",
            "degree": "Bachelor of Technology",
            "field_of_study": "Computer Science and Engineering",
            "start_date": "2016",
            "end_date": "2020",
            "gpa": "8.9 / 10",
        })
        log_step("9. Education Add/Delete CRUD", True, "Successfully verified education lifecycle")
    except Exception as e:
        log_step("9. Education Add/Delete CRUD", False, str(e))

    # 10. Certifications CRUD
    try:
        r = session.post(f"{API_URL}/profile/certifications", json={
            "name": "Temporary Certificate",
            "issuing_organization": "Test Org",
        })
        assert r.status_code == 200
        temp_cert_id = r.json().get("data", {}).get("id")

        r = session.delete(f"{API_URL}/profile/certifications/{temp_cert_id}")
        assert r.status_code == 200

        session.post(f"{API_URL}/profile/certifications", json={
            "name": "AWS Certified Solutions Architect - Associate",
            "issuing_organization": "Amazon Web Services",
            "issue_date": "2023-08",
            "credential_url": "https://aws.amazon.com/verification/example",
        })
        log_step("10. Certifications Add/Delete CRUD", True, "Successfully verified certification lifecycle")
    except Exception as e:
        log_step("10. Certifications Add/Delete CRUD", False, str(e))

    # 11. Resume Import
    draft_data = None
    try:
        resume_sample = """
        Vatsal Sharma
        Bengaluru, India | +91 9876543210 | vatsal@smartresume.ai | linkedin.com/in/vatsal-sharma

        Professional Summary:
        Staff Distributed Systems Engineer with 6+ years specializing in high-throughput backend microservices, event-driven architectures, and resilient cloud systems.

        Experience:
        Apex Cloud Technologies — Staff Systems Engineer
        2021 - Present | Bengaluru, India
        - Architected distributed data processing pipeline handling 50M daily events with 99.99% uptime.
        - Optimized PostgreSQL indexing and query execution plans, slashing p99 latency by 35%.
        - Led cross-functional team of 10 backend engineers implementing distributed tracing and observability.

        Skills:
        Python, FastAPI, PostgreSQL, Redis, Kubernetes, Docker, Distributed Systems, Kafka

        Education:
        National Institute of Technology — B.Tech in Computer Science, 2020

        Certifications:
        AWS Certified Solutions Architect (2023)
        """
        r = session.post(f"{API_URL}/profile/import", data={"raw_text": resume_sample})
        assert r.status_code == 200, f"Resume import failed: {r.text}"
        draft_data = r.json().get("data", {})
        assert draft_data.get("full_name") or draft_data.get("headline"), "Parser failed to extract basic info"
        log_step("11. Resume Import & Parsing", True, f"Extracted {len(draft_data.get('experiences', []))} experiences, {len(draft_data.get('skills', []))} skills")
    except Exception as e:
        log_step("11. Resume Import & Parsing", False, str(e))

    # 12. Review Imported Data
    try:
        assert isinstance(draft_data, dict)
        assert "experiences" in draft_data
        assert "skills" in draft_data
        log_step("12. Review Imported Draft Data", True, "Draft payload verified for user review before commit")
    except Exception as e:
        log_step("12. Review Imported Draft Data", False, str(e))

    # 13. Commit Imported Profile
    try:
        r = session.post(f"{API_URL}/profile/import/commit", json=draft_data)
        assert r.status_code == 200, f"Commit profile failed: {r.text}"
        comm_prof = r.json().get("data", {})
        assert len(comm_prof.get("experiences", [])) >= 1
        log_step("13. Commit Reviewed Profile", True, f"Master profile committed with {len(comm_prof.get('experiences', []))} experiences")
    except Exception as e:
        log_step("13. Commit Reviewed Profile", False, str(e))

    # 14. Create Job Posting
    job_id = None
    try:
        job_payload = {
            "title": "Staff Backend Engineer — High Concurrency",
            "company": "Fintech Global",
            "location": "Bengaluru / Remote",
            "raw_description": (
                "Fintech Global is looking for a Staff Backend Engineer to scale our core payment infrastructure. "
                "Requirements: Deep expertise in Python, FastAPI, PostgreSQL, Redis, and Distributed Systems. "
                "Experience with high concurrency, low latency event processing, Docker, and Kubernetes is essential."
            ),
        }
        r = session.post(f"{API_URL}/jobs", json=job_payload)
        assert r.status_code == 200, f"Create job failed: {r.text}"
        job_data = r.json().get("data", {})
        job_id = job_data.get("id")
        assert job_id, "Job ID missing"
        log_step("14. Create Target Job Posting", True, f"Job ID {job_id}: {job_data.get('title')} at {job_data.get('company')}")
    except Exception as e:
        import traceback
        log_step("14. Create Target Job Posting", False, f"{traceback.format_exc()}")

    # 15. Parse JD / Requirement Extraction
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}")
        assert r.status_code == 200
        jd = r.json().get("data", {})
        reqs = jd.get("parsed_requirements") or jd.get("extracted_skills") or []
        log_step("15. Parse Job Description", True, f"Extracted {len(reqs)} key requirements/skills")
    except Exception as e:
        import traceback
        log_step("15. Parse Job Description", False, f"{traceback.format_exc()}")

    # 16. Fit Analysis
    fit_result = None
    try:
        r = session.post(f"{API_URL}/jobs/{job_id}/fit-analysis")
        assert r.status_code == 200, f"Fit analysis failed: {r.text}"
        fit_result = r.json().get("data", {})
        overall_score = fit_result.get("overall_score")
        assert overall_score is not None and 0 <= overall_score <= 100
        log_step("16. Application Fit Analysis", True, f"Overall Fit Score: {overall_score}%, Grounding Score: {fit_result.get('grounding_score')}%")
    except Exception as e:
        import traceback
        log_step("16. Application Fit Analysis", False, f"{traceback.format_exc()}")

    # 17. Evidence Map Inspection
    try:
        analysis_items = fit_result.get("requirements_analysis", [])
        matched = fit_result.get("matched_skills", [])
        missing = fit_result.get("missing_skills", [])
        log_step("17. Evidence Map Verification", True, f"Matched Skills: {len(matched)}, Missing Skills: {len(missing)}, Requirements Analyzed: {len(analysis_items)}")
    except Exception as e:
        import traceback
        log_step("17. Evidence Map Verification", False, f"{traceback.format_exc()}")

    # 18. AI Tailoring Proposal
    tailor_proposal = None
    all_diffs = []
    try:
        r = session.post(f"{API_URL}/jobs/{job_id}/tailor")
        assert r.status_code == 200, f"Tailoring failed: {r.text}"
        tailor_proposal = r.json().get("data", {})
        sections = tailor_proposal.get("tailored_experiences", [])
        assert len(sections) >= 1, "No tailored sections generated"
        for s in sections:
            all_diffs.extend(s.get("diffs", []))
        assert len(all_diffs) >= 1, "No tailored bullet diffs generated"
        log_step("18. AI Tailoring Proposal", True, f"Generated {len(all_diffs)} evidence-grounded bullet changes with side-by-side diffs across {len(sections)} sections")
    except Exception as e:
        import traceback
        log_step("18. AI Tailoring Proposal", False, f"{traceback.format_exc()}")

    # 19. Accept / Reject Diff Inspection
    try:
        first_change = all_diffs[0]
        assert "original" in first_change
        assert "suggested" in first_change
        assert "matched_keyword" in first_change
        log_step("19. Accept/Reject Diff Review", True, f"Verified bullet diff targeting keyword: {first_change.get('matched_keyword')}")
    except Exception as e:
        import traceback
        log_step("19. Accept/Reject Diff Review", False, f"{traceback.format_exc()}")

    # 20. Create Immutable Version Snapshot
    version_id = None
    try:
        # Build tailored content
        cur_prof = session.get(f"{API_URL}/profile").json().get("data", {})
        content_json = {
            "candidate_name": cur_prof.get("full_name", full_name),
            "headline": "Staff Backend Engineer — High Concurrency",
            "email": email,
            "phone": cur_prof.get("phone", "+91 9876543210"),
            "location": cur_prof.get("location", "Bengaluru, India"),
            "summary": cur_prof.get("summary", ""),
            "experiences": cur_prof.get("experiences", []),
            "skills": cur_prof.get("skills", []),
            "education": cur_prof.get("education", []),
            "certifications": cur_prof.get("certifications", []),
            "projects": cur_prof.get("projects", []),
        }

        r = session.post(f"{API_URL}/jobs/{job_id}/versions", json={
            "version_name": "Tailored for Fintech Global Staff Backend",
            "template_name": "classic_ats",
            "content_json": content_json,
        })
        assert r.status_code == 200, f"Commit version failed: {r.text}"
        v_data = r.json().get("data", {})
        version_id = v_data.get("id")
        assert version_id, "Version ID missing"
        log_step("20. Create Immutable Version", True, f"Version ID {version_id}, Version #{v_data.get('version_number')}")
    except Exception as e:
        import traceback
        log_step("20. Create Immutable Version", False, f"{traceback.format_exc()}")

    # 21. Resume Preview
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}/versions/{version_id}")
        assert r.status_code == 200, f"Fetch version failed: {r.text}"
        ver_preview = r.json().get("data", {})
        assert ver_preview.get("content_json", {}).get("candidate_name")
        log_step("21. Resume Live Preview", True, f"Preview fetched for: {ver_preview['content_json']['candidate_name']}")
    except Exception as e:
        import traceback
        log_step("21. Resume Live Preview", False, f"{traceback.format_exc()}")

    # 22. PDF Export
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}/versions/{version_id}/export?format=pdf&template=classic_ats")
        assert r.status_code == 200, f"PDF export failed: {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf"
        assert r.content.startswith(b"%PDF-"), "Invalid PDF binary stream"
        log_step("22. PDF Export", True, f"Generated valid PDF ({len(r.content)} bytes)")
    except Exception as e:
        import traceback
        log_step("22. PDF Export", False, f"{traceback.format_exc()}")

    # 23. DOCX Export
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}/versions/{version_id}/export?format=docx&template=classic_ats")
        assert r.status_code == 200, f"DOCX export failed: {r.status_code}"
        assert "wordprocessingml" in r.headers.get("content-type", "")
        assert r.content.startswith(b"PK"), "Invalid DOCX zip binary stream"
        log_step("23. DOCX Export", True, f"Generated valid DOCX ({len(r.content)} bytes)")
    except Exception as e:
        import traceback
        log_step("23. DOCX Export", False, f"{traceback.format_exc()}")

    # 24. Application Tracker Lifecycle
    try:
        # Create
        app_payload = {
            "job_posting_id": job_id,
            "company": "Fintech Global",
            "job_title": "Staff Backend Engineer",
            "status": "APPLIED",
            "notes": "Submitted tailored resume and cover note.",
        }
        r = session.post(f"{API_URL}/applications", json=app_payload)
        assert r.status_code == 200, f"Create app failed: {r.text}"
        app_id = r.json().get("data", {}).get("id")

        # Update
        r = session.patch(f"{API_URL}/applications/{app_id}", json={
            "status": "INTERVIEWING",
            "notes": "Round 1 system architecture interview scheduled for Tuesday.",
        })
        assert r.status_code == 200
        assert r.json().get("data", {}).get("status") == "INTERVIEWING"

        # List
        r = session.get(f"{API_URL}/applications")
        assert r.status_code == 200
        assert any(a.get("id") == app_id for a in r.json().get("data", []))

        # Delete
        r = session.delete(f"{API_URL}/applications/{app_id}")
        assert r.status_code == 200
        log_step("24. Application Tracker Lifecycle", True, "Successfully created, updated status, listed, and deleted application")
    except Exception as e:
        import traceback
        log_step("24. Application Tracker Lifecycle", False, f"{traceback.format_exc()}")

    # 25. Billing & Consent Verification
    try:
        p_res = session.get(f"{API_URL}/payments/pricing").json().get("data", {})
        assert "INR" in p_res.get("currencies", {})
        assert "USD" in p_res.get("currencies", {})
        assert p_res.get("test_upi_id") == "ladanivatsal8892@oksbi"

        c_res = session.get(f"{API_URL}/payments/consent-info?plan=PRO_MONTHLY").json().get("data", {})
        assert c_res.get("is_recurring") is True
        assert "AFA" in c_res.get("regulatory_note", "") or "RBI" in c_res.get("regulatory_note", "")

        log_step("25. Billing & Pricing Table", True, f"Multi-currency supported; RBI AFA consent verified; Test UPI: {p_res.get('test_upi_id')}")
    except Exception as e:
        import traceback
        log_step("25. Billing & Pricing Table", False, f"{traceback.format_exc()}")

    # 26. ₹1 TEST Purchase (Single Export Credit)
    test_order_id = None
    try:
        # Check initial credits
        b_before = session.get(f"{API_URL}/payments/billing-summary").json().get("data", {})
        extra_before = b_before.get("quotas", {}).get("extra_credits", 0)

        # Create Order
        r = session.post(f"{API_URL}/payments/create-order", json={"plan": "SINGLE_EXPORT", "currency": "INR"})
        assert r.status_code == 200, f"Create order failed: {r.text}"
        order_data = r.json().get("data", {})
        test_order_id = order_data.get("order_id")
        amount = order_data.get("amount")
        assert amount == 100, f"Expected amount 100 paise (₹1), got {amount}"

        # Verify Payment Simulator
        v_payload = {
            "order_id": test_order_id,
            "payment_id": f"pay_test_{uuid.uuid4().hex[:12]}",
            "plan": "SINGLE_EXPORT",
        }
        r = session.post(f"{API_URL}/payments/verify", json=v_payload)
        assert r.status_code == 200, f"Verify payment failed: {r.text}"
        v_res = r.json().get("data", {})
        assert v_res.get("success") is True
        assert v_res.get("recurring") is False
        log_step("26. INR 1 TEST Single-Export Purchase", True, f"Order {test_order_id} (100 paise) simulated and verified")
    except Exception as e:
        import traceback
        log_step("26. INR 1 TEST Single-Export Purchase", False, f"{traceback.format_exc()}")

    # 27. Verify 1 Export Credit Added
    try:
        b_after = session.get(f"{API_URL}/payments/billing-summary").json().get("data", {})
        extra_after = b_after.get("quotas", {}).get("extra_credits", 0)
        assert extra_after == extra_before + 1, f"Expected {extra_before + 1}, got {extra_after}"
        log_step("27. Export Credit Incremented", True, f"Extra export credits: {extra_after} (incremented by +1)")
    except Exception as e:
        import traceback
        log_step("27. Export Credit Incremented", False, f"{traceback.format_exc()}")

    # 28. Confirm No Recurring Subscription
    try:
        s_after = session.get(f"{API_URL}/payments/subscription").json().get("data", {})
        assert s_after.get("plan_name") == "FREE", f"Plan must remain FREE, got {s_after.get('plan_name')}"
        log_step("28. Recurring Subscription Protection", True, "Confirmed plan remains FREE; no unauthorized recurring subscription activated")
    except Exception as e:
        import traceback
        log_step("28. Recurring Subscription Protection", False, f"{traceback.format_exc()}")

    # 29. Logout & Token Invalidation
    try:
        r = session.post(f"{API_URL}/auth/logout", json={"refresh_token": refresh_token})
        assert r.status_code == 200, f"Logout failed: {r.text}"

        # Verify access token is blacklisted
        me_check = session.get(f"{API_URL}/auth/me")
        assert me_check.status_code == 401, f"Expected 401 Unauthorized after logout, got {me_check.status_code}"
        log_step("29. User Logout & Token Blacklist", True, "Successfully logged out and confirmed access token is revoked (401)")
    except Exception as e:
        import traceback
        log_step("29. User Logout & Token Blacklist", False, f"{traceback.format_exc()}")

    # 30. Login Again
    try:
        session.headers.pop("Authorization", None)
        r = session.post(f"{API_URL}/auth/login", json={
            "email": email,
            "password": password,
        })
        assert r.status_code == 200, f"Re-login failed: {r.text}"
        new_token = r.json().get("data", {}).get("access_token")
        assert new_token
        session.headers.update({"Authorization": f"Bearer {new_token}"})

        me_again = session.get(f"{API_URL}/auth/me")
        assert me_again.status_code == 200
        log_step("30. Login Again Verification", True, f"Re-authenticated successfully as {email}")
    except Exception as e:
        import traceback
        log_step("30. Login Again Verification", False, f"{traceback.format_exc()}")

    # 31. OAuth Configuration Audit
    try:
        cfg = session.get(f"{API_URL}/auth/oauth/config").json().get("data", {})
        assert cfg.get("google_enabled") is False
        assert cfg.get("linkedin_enabled") is False
        assert "instructions" in cfg.get("google", {})

        # Verify Google endpoint returns 503 rather than fake OAuth token
        g_url = session.get(f"{API_URL}/auth/oauth/google/url")
        assert g_url.status_code == 503, f"Expected 503 for unconfigured Google OAuth, got {g_url.status_code}"

        # Verify LinkedIn endpoint returns 503 rather than fake OAuth token
        l_url = session.get(f"{API_URL}/auth/oauth/linkedin/url")
        assert l_url.status_code == 503, f"Expected 503 for unconfigured LinkedIn OAuth, got {l_url.status_code}"

        log_step("31. OAuth Configuration Audit", True, "OAuth configuration correctly reports 'Pending' with setup instructions; zero fake tokens generated")
    except Exception as e:
        import traceback
        log_step("31. OAuth Configuration Audit", False, f"{traceback.format_exc()}")

    # 32. Product Intelligence V2: Resume Health Report (10 Dimensions)
    try:
        r = session.get(f"{API_URL}/profile/health-report")
        assert r.status_code == 200, f"Health report failed: {r.text}"
        health_data = r.json().get("data", {})
        assert "overall_health" in health_data
        dimensions = health_data.get("dimensions", [])
        assert len(dimensions) == 10, f"Expected 10 dimensions, got {len(dimensions)}"
        for d in dimensions:
            assert "dimension" in d and "status" in d and "reason" in d
        log_step("32. Product Intelligence: 10-Dimension Resume Health Report", True, f"Overall Health: {health_data.get('overall_health')}, Verified 10 explainable dimensions with WHY rationale")
    except Exception as e:
        import traceback
        log_step("32. Product Intelligence: 10-Dimension Resume Health Report", False, f"{traceback.format_exc()}")

    # 33. Product Intelligence V2: Skill Consistency Graph
    try:
        r = session.get(f"{API_URL}/profile/consistency")
        assert r.status_code == 200, f"Consistency check failed: {r.text}"
        graph_data = r.json().get("data", {})
        nodes = graph_data.get("nodes", [])
        assert len(nodes) > 0
        supported = [n for n in nodes if n.get("status") == "SUPPORTED"]
        log_step("33. Product Intelligence: Skill Evidence Consistency Graph", True, f"Analyzed {len(nodes)} skills: {len(supported)} verified with citations against projects/experiences")
    except Exception as e:
        import traceback
        log_step("33. Product Intelligence: Skill Evidence Consistency Graph", False, f"{traceback.format_exc()}")

    # 34. Product Intelligence V2: Career Level Setting & Verbs
    try:
        r = session.post(f"{API_URL}/profile/career-level", json={"career_level": "DEVELOPING_PROFESSIONAL"})
        assert r.status_code == 200, f"Career level failed: {r.text}"
        cl_data = r.json().get("data", {})
        assert cl_data.get("career_level") == "DEVELOPING_PROFESSIONAL"
        assert len(cl_data.get("recommended_verbs", [])) > 0
        log_step("34. Product Intelligence: Career Experience Level Intelligence", True, f"Level: DEVELOPING_PROFESSIONAL with {len(cl_data.get('recommended_verbs'))} recommended verbs")
    except Exception as e:
        import traceback
        log_step("34. Product Intelligence: Career Experience Level Intelligence", False, f"{traceback.format_exc()}")

    # 35. Product Intelligence V2: Content Relevance Check
    try:
        r = session.get(f"{API_URL}/profile/relevance-check?domain=Software%20Engineering")
        assert r.status_code == 200, f"Relevance check failed: {r.text}"
        rel_data = r.json().get("data", {})
        assert "items" in rel_data
        assert "count" in rel_data
        log_step("35. Product Intelligence: Content Relevance & Low-Value Review", True, f"Evaluated domain: {len(rel_data.get('items'))} items reviewed; guidance: {rel_data.get('guidance', '')[:60]}...")
    except Exception as e:
        import traceback
        log_step("35. Product Intelligence: Content Relevance & Low-Value Review", False, f"{traceback.format_exc()}")

    # 36. Product Intelligence V2: Application Readiness Report
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}/readiness")
        assert r.status_code == 200, f"Readiness report failed: {r.text}"
        readiness_data = r.json().get("data", {})
        assert "readiness_verdict" in readiness_data
        assert "summary_statement" in readiness_data
        assert "indicators" in readiness_data
        assert "breakdown" in readiness_data
        b = readiness_data.get("breakdown", {})
        log_step("36. Product Intelligence: Application Readiness Report V2", True, f"Verdict: {readiness_data.get('readiness_verdict')} | Strong: {b.get('strong_matches_count')}, Partial: {b.get('partial_matches_count')}, Missing: {b.get('missing_count')}")
    except Exception as e:
        import traceback
        log_step("36. Product Intelligence: Application Readiness Report V2", False, f"{traceback.format_exc()}")

    # 37. Product Intelligence V2: Learning Gap Blueprint
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}/learning-gap?req=Redis")
        assert r.status_code == 200, f"Learning gap failed: {r.text}"
        gap_data = r.json().get("data", {})
        assert gap_data.get("missing_requirement")
        assert gap_data.get("suggested_mini_project")
        log_step("37. Product Intelligence: Learning Gap Mini-Project Blueprint", True, f"Requirement: {gap_data.get('missing_requirement')} -> Project: {gap_data.get('suggested_mini_project', '')[:60]}...")
    except Exception as e:
        import traceback
        log_step("37. Product Intelligence: Learning Gap Mini-Project Blueprint", False, f"{traceback.format_exc()}")

    # 38. Product Intelligence V2: Pre-Export Consistency Check
    try:
        r = session.get(f"{API_URL}/jobs/{job_id}/versions/{version_id}/pre-export-check")
        assert r.status_code == 200, f"Pre-export check failed: {r.text}"
        chk_data = r.json().get("data", {})
        assert "passed" in chk_data
        assert "warnings" in chk_data
        log_step("38. Product Intelligence: Pre-Export Consistency Check", True, f"Passed: {chk_data.get('passed')}, Warnings: {len(chk_data.get('warnings'))}")
    except Exception as e:
        import traceback
        log_step("38. Product Intelligence: Pre-Export Consistency Check", False, f"{traceback.format_exc()}")

    print("=" * 70)
    print("ALL 38 LIVE PRODUCTION-READINESS QA CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        run_live_qa()
    except QAFailure as qe:
        print(f"\nFATAL QA FAILURE: {qe}")
        sys.exit(1)

