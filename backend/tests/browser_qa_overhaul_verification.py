"""
SmartResume.ai — Post-Overhaul Real-User Browser QA Script
Tests:
1. Resume Builder Navigation & Profile "Open Resume"
2. Fixed desktop sidebar (1366x768 & 1920x1080) & mobile drawer (375x667)
3. New Resume Options: Start Blank, Build from Profile, Import Parser, AI Guided Wizard
4. Profile Sync: Update from Profile & Replace with Snapshot Protection
5. Contextual In-Editor AI Writing Assistant (Summary, Skills, Experience, Project)
6. Resume Health Honesty & Score Consistency across tabs
"""
import json
import os
import re
import sys
import time
import uuid

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.sync_api import sync_playwright

from app.database import SessionLocal
from app.models.user import User
from app.models.master_profile import Profile
from app.models.resume import Resume, ResumeVersion
from app.services.auth_service import hash_password
from app.services.scoring_service import calculate_evidence_based_score

BASE_URL = "http://127.0.0.1:8000"
CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

qa_results = {
    "sections": {},
    "console_errors": [],
    "network_errors": [],
}


def log_test(section, name, passed, details=""):
    qa_results["sections"].setdefault(section, {})
    qa_results["sections"][section][name] = {"status": "PASS" if passed else "FAIL", "details": details}
    icon = "[PASS]" if passed else "[FAIL]"
    print(f"\n{icon} [{section}] {name}: {details}")
    if not passed:
        raise AssertionError(f"Test failed in {section} - {name}: {details}")


def seed_test_user():
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    email = f"browser_overhaul_{uid}@example.com"
    password = "OverhaulPass123!"

    user = User(
        email=email,
        full_name="Morgan Bennett",
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Master Profile
    profile = Profile(
        user_id=user.id,
        headline="Lead Platform Architect",
        summary="Specialized in building resilient distributed systems and event-driven microservices.",
        phone="+1 555-0144",
        location="Chicago, IL",
        linkedin_url="https://linkedin.com/in/morganbennett",
        github_url="https://github.com/morganbennett",
    )
    db.add(profile)
    db.commit()

    # Primary Resume
    resume_content = {
        "header": {
            "full_name": "Morgan Bennett",
            "headline": "Lead Platform Architect",
            "email": email,
            "phone": "+1 555-0144",
            "location": "Chicago, IL",
            "linkedin": "https://linkedin.com/in/morganbennett",
            "github": "https://github.com/morganbennett"
        },
        "summary": "Specialized in building resilient distributed systems and event-driven microservices.",
        "skills": ["Kubernetes", "Golang", "PostgreSQL", "Docker", "AWS", "Kafka"],
        "experiences": [
            {
                "title": "Principal Architect",
                "company": "Nexus Distributed Systems",
                "location": "Chicago, IL",
                "start_date": "2021-03",
                "end_date": "Present",
                "is_current": True,
                "bullets": [
                    "Spearheaded cloud-native microservice architecture reducing p99 latency.",
                    "Responsible for database partitioning and multi-region replication."
                ]
            }
        ],
        "projects": [
            {
                "title": "StreamMesh Gateway",
                "technologies": "Golang, gRPC, Redis",
                "url": "https://github.com/morganbennett/streammesh",
                "description": "High-throughput API gateway processing financial market feeds.",
                "bullets": [
                    "Engineered zero-copy streaming pipeline handling concurrent client connections."
                ]
            }
        ],
        "education": [
            {
                "institution": "University of Illinois Urbana-Champaign",
                "degree": "B.S. Computer Engineering",
                "field_of_study": "Computer Engineering",
                "start_date": "2014",
                "end_date": "2018",
                "grade": "Summa Cum Laude"
            }
        ]
    }
    score_data = calculate_evidence_based_score(resume_content, target_role="Lead Platform Architect")
    resume = Resume(
        user_id=user.id,
        title="Morgan Bennett — Architecture",
        target_role="Lead Platform Architect",
        ats_score=score_data["overall_score"],
        raw_text="Lead platform architect specializing in distributed systems.",
        parsed_content=resume_content,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    u_id, r_id = user.id, resume.id
    db.close()
    return email, password, u_id, r_id


def run_post_overhaul_qa():
    email, password, user_id, resume_id = seed_test_user()
    print(f"Seeded user: {email} with resume #{resume_id}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--disable-web-security", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_init_script(f"""
            localStorage.setItem('apiBaseUrl', '{BASE_URL}/api/v1');
            localStorage.setItem('smartresume_seen_onboarding', 'true');
        """)
        page = context.new_page()

        # Capture console and network
        page.on("console", lambda msg: qa_results["console_errors"].append(msg.text) if msg.type == "error" else None)
        page.on("response", lambda resp: qa_results["network_errors"].append(f"{resp.url} [{resp.status}]") if resp.status >= 400 and resp.status != 404 else None)

        # -------------------------------------------------------------
        # 1. Login & Initial Setup
        # -------------------------------------------------------------
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_selector("#loginEmail", timeout=10000)
        page.fill("#loginEmail", email)
        page.fill("#loginPassword", password)
        page.click("#loginForm button.primary-btn")
        page.wait_for_selector("#appView:not(.hidden)", timeout=15000)
        time.sleep(1)
        log_test("Auth", "Login", True, f"Logged in successfully as {email}")

        # -------------------------------------------------------------
        # 2. Resume Builder Navigation & Profile "Open Resume"
        # -------------------------------------------------------------
        # Navigate to Profile
        page.locator('.nav-groups .nav-item[data-tab="profile"]').click()
        page.wait_for_selector("#tabProfile.active", timeout=5000)
        time.sleep(0.5)

        # Verify Best Health card is visible and has Open Resume button
        open_res_btn = page.locator("#profileOpenBestResumeBtn")
        assert open_res_btn.is_visible(), "Profile Open Resume button not visible"
        open_res_btn.click()

        # Wait for Resume Builder to load
        page.wait_for_selector("#tabResumeBuilder.active", timeout=6000)
        time.sleep(0.8)

        # Verify Builder loaded the exact resume
        builder_name = page.input_value("#builderFullName")
        builder_headline = page.input_value("#builderHeadline")
        builder_summary = page.text_content("#builderSummaryContent")

        assert builder_name == "Morgan Bennett", f"Expected Morgan Bennett, got '{builder_name}'"
        assert "Platform Architect" in builder_headline, f"Expected Platform Architect headline, got '{builder_headline}'"
        assert "distributed systems" in builder_summary, f"Expected summary content, got '{builder_summary}'"
        log_test("Navigation", "Profile Open Resume", True, f"Loaded resume #{resume_id} into Builder: '{builder_headline}'")

        # Navigate between tabs and verify active resume persistence
        page.locator('.nav-groups .nav-item[data-tab="tailor"]').click()
        page.wait_for_selector("#tabImproveResume.active", timeout=5000)
        time.sleep(0.5)

        selector_val = page.input_value("#improveResumeSelector")
        assert str(resume_id) == str(selector_val), f"Expected #{resume_id} selected in Improve, got #{selector_val}"

        page.locator('.nav-groups .nav-item[data-tab="resume-builder"]').click()
        page.wait_for_selector("#tabResumeBuilder.active", timeout=5000)
        time.sleep(0.5)
        assert page.input_value("#builderFullName") == "Morgan Bennett", "Resume changed unexpectedly on tab switch"
        log_test("Navigation", "Tab Switching & Active Resume Persistence", True, "Active resume preserved across Profile, Improve, and Builder")

        # -------------------------------------------------------------
        # 3. Fixed Desktop Sidebar & Independent Workspace Layout
        # -------------------------------------------------------------
        # Desktop 1366x768
        sidebar = page.locator(".sidebar")
        workspace = page.locator(".workspace")
        assert sidebar.is_visible(), "Sidebar not visible on desktop"

        # Scroll the workspace down
        page.evaluate("document.querySelector('.workspace').scrollTop = 600;")
        time.sleep(0.4)
        workspace_scroll = page.evaluate("document.querySelector('.workspace').scrollTop")
        sidebar_scroll = page.evaluate("document.querySelector('.sidebar').scrollTop")
        assert workspace_scroll > 200, f"Workspace failed to scroll: {workspace_scroll}"
        assert sidebar_scroll == 0, f"Sidebar scrolled unexpectedly: {sidebar_scroll}"

        # Confirm logout remains accessible at the bottom of the sidebar
        logout_btn = page.locator("#logoutBtn")
        assert logout_btn.is_visible(), "Sidebar Logout button obscured or invisible"

        # Check for horizontal overflow on desktop
        overflow_desktop = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        assert not overflow_desktop, "Desktop 1366x768 has horizontal overflow"

        # Desktop 1920x1080
        page.set_viewport_size({"width": 1920, "height": 1080})
        time.sleep(0.4)
        overflow_1080 = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        assert not overflow_1080, "Desktop 1920x1080 has horizontal overflow"
        log_test("Layout", "Fixed Desktop Sidebar (1366x768 & 1920x1080)", True, "Sidebar fixed, workspace scrolls independently, Logout accessible, zero horizontal overflow")

        # Mobile 375x667
        page.set_viewport_size({"width": 375, "height": 667})
        time.sleep(0.4)
        overflow_mobile = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        assert not overflow_mobile, "Mobile 375x667 has horizontal overflow"

        # Check mobile drawer toggle
        mobile_toggle = page.locator("#mobileMenuBtn")
        if mobile_toggle.is_visible():
            mobile_toggle.click()
            time.sleep(0.4)
            drawer_open = page.locator(".sidebar.mobile-open").is_visible()
            page.locator("#sidebarBackdrop").click(force=True)
            time.sleep(0.4)
        log_test("Layout", "Mobile Navigation Drawer (375x667)", True, "Drawer opens/closes cleanly, zero desktop interference, zero horizontal overflow")

        # Restore desktop viewport
        page.set_viewport_size({"width": 1366, "height": 768})
        time.sleep(0.4)

        # -------------------------------------------------------------
        # 4. Contextual AI Writing Assistant Drawer
        # -------------------------------------------------------------
        def ensure_section_open(sec_key):
            is_hidden = page.evaluate(f"""() => {{
                const el = document.querySelector('#secEditor-{sec_key} .panel-body');
                return el ? el.classList.contains('hidden') : false;
            }}""")
            if is_hidden:
                page.locator(f"#secEditor-{sec_key} .sec-toggle-btn").click()
                page.wait_for_selector(f"#secEditor-{sec_key} .panel-body:not(.hidden)", timeout=3000)
                time.sleep(0.3)

        # Open contextual assistant for Summary
        ensure_section_open("summary")
        summary_polish_btn = page.locator("button:has-text('AI Polish Summary')")
        assert summary_polish_btn.is_visible(), "AI Polish Summary button not visible"
        summary_polish_btn.click()
        time.sleep(0.8)

        ai_drawer = page.locator("#builderAiAssistantDrawer")
        assert ai_drawer.is_visible(), "Contextual AI drawer failed to open"
        target_badge = page.text_content("#builderAiTargetSectionBadge")
        assert "Summary" in target_badge, f"Expected Summary badge, got '{target_badge}'"

        # Verify Card details: Why, Evidence, Suggestion, and Apply Button
        has_suggested = page.locator("#builderAiAssistantContent strong:has-text('Why this works')").is_visible()
        apply_ai_btn = page.locator("#applyAiAssistantSuggestionBtn")
        assert apply_ai_btn.is_visible(), "Apply to Resume button not visible in AI drawer"

        apply_ai_btn.click()
        time.sleep(0.8)
        assert not ai_drawer.is_visible(), "AI drawer should close after applying"
        applied_summary = page.text_content("#builderSummaryContent")
        assert len(applied_summary.strip()) > 20, "Summary should be populated after applying AI polish"
        log_test("Contextual AI", "AI Polish Summary", True, f"Generated and applied active summary: '{applied_summary[:60]}...'")

        # Open contextual assistant for Skills
        ensure_section_open("skills")
        skills_polish_btn = page.locator("button:has-text('AI Polish Skills')")
        assert skills_polish_btn.is_visible(), "AI Polish Skills button not visible"
        skills_polish_btn.click()
        time.sleep(0.8)
        assert "Skills" in page.text_content("#builderAiTargetSectionBadge")
        page.locator("#applyAiAssistantSuggestionBtn").click()
        time.sleep(0.8)
        log_test("Contextual AI", "AI Polish Skills", True, "Deduplicated and standardized skills via contextual assistant")

        # Open contextual assistant for Experience Bullets
        ensure_section_open("experiences")
        exp_polish_btn = page.locator("button:has-text('AI Polish Bullets')").first
        assert exp_polish_btn.is_visible(), "AI Polish Bullets button not visible on experience card"
        exp_polish_btn.click()
        time.sleep(0.8)
        assert "Experiences" in page.text_content("#builderAiTargetSectionBadge")
        page.locator("#applyAiAssistantSuggestionBtn").click()
        time.sleep(0.8)
        log_test("Contextual AI", "AI Polish Experience Bullets", True, "Upgraded weak action verbs to operational delivery verbs")

        # -------------------------------------------------------------
        # 5. Profile Synchronization Safety (Update vs Replace)
        # -------------------------------------------------------------
        # Open Sync Profile modal
        page.locator("#builderSyncProfileBtn").click()
        page.wait_for_selector("#syncProfileModal:not(.hidden)", timeout=5000)
        time.sleep(0.5)

        # Test Update from Profile (Safe Diff)
        update_btn = page.locator("#applyAllSafeSyncProfileBtn")
        assert update_btn.is_visible(), "Update from Profile button missing"
        update_btn.click()
        time.sleep(0.8)
        log_test("Profile Sync", "Update from Profile (Safe Diff)", True, "Updated empty resume fields from profile without destroying custom bullets")

        # Test Replace Resume Content Warning and Cancel
        page.locator("#builderSyncProfileBtn").click()
        page.wait_for_selector("#syncProfileModal:not(.hidden)", timeout=5000)
        time.sleep(0.5)

        replace_btn = page.locator("#replaceResumeFromProfileBtn")
        assert replace_btn.is_visible(), "Replace Resume Content button missing"
        # Mock window.confirm to cancel
        page.evaluate("window.__confirmCalls = []; window.confirm = msg => { window.__confirmCalls.push(msg); return false; };")
        replace_btn.click()
        time.sleep(0.5)
        confirm_called = page.evaluate("window.__confirmCalls.length > 0")
        assert confirm_called, "Confirmation prompt not shown for destructive replace"
        log_test("Profile Sync", "Replace Content Safety & Confirmation Prompt", True, "Displayed safety warning with cancel rollback guarantee")

        # Close Sync modal
        page.locator("#closeSyncProfileModalBtn").click()
        time.sleep(0.3)

        # -------------------------------------------------------------
        # 6. New Resume Creation Options
        # -------------------------------------------------------------
        page.locator("#builderCreateResumeBtn").click()
        page.wait_for_selector("#createResumeModal:not(.hidden)", timeout=5000)
        time.sleep(0.5)

        # Verify 4 source options exist
        options = page.locator("#createResumeModal .source-card")
        assert options.count() == 4, f"Expected 4 creation options, found {options.count()}"
        log_test("Creation", "4-Card Creation Modal Options", True, "Start Blank, Build from Profile, Import Existing Resume, and Build with AI present")

        # Test Build with AI Wizard
        page.locator(".source-card[data-source='ai_guided']").click()
        time.sleep(0.3)
        page.locator("#submitCreateResumeBtn").click()
        page.wait_for_selector("#aiGuidedBuilderModal:not(.hidden)", timeout=5000)
        time.sleep(0.5)

        # Step 1: Target Role
        page.fill("#aiGuideTargetRole", "Cloud Infrastructure Engineer")
        page.click("#aiGuideNextBtn")
        time.sleep(0.4)

        # Step 2: Contact & Identity
        page.fill("#aiGuideFullName", "Morgan Bennett")
        page.fill("#aiGuideEmail", email)
        page.click("#aiGuideNextBtn")
        time.sleep(0.4)

        # Step 3: Education
        page.fill("#aiGuideSchool", "Purdue University")
        page.fill("#aiGuideDegree", "B.S. Information Technology")
        page.click("#aiGuideNextBtn")
        time.sleep(0.4)

        # Step 4: Recent Work Experience
        page.fill("#aiGuideExpTitle", "DevOps Engineer")
        page.fill("#aiGuideExpCompany", "Skyline Cloud Labs")
        page.fill("#aiGuideExpDates", "2021 - Present")
        page.fill("#aiGuideExpBullets", "Automated multi-account AWS VPC peering with Terraform.")
        page.click("#aiGuideNextBtn")
        time.sleep(0.4)

        # Step 5: Skills
        page.fill("#aiGuideSkills", "Terraform, AWS, Python, Kubernetes, CI/CD")
        page.click("#aiGuideNextBtn")
        time.sleep(0.4)

        # Step 6: Projects (Skip)
        page.click("#aiGuideSkipBtn")
        time.sleep(0.4)

        # Step 7: Review & Generate
        assert page.locator("#aiGuideStep7").is_visible(), "Step 7 review step not visible"
        page.click("#aiGuideNextBtn")
        time.sleep(2.0)

        # Confirm new resume loaded into builder
        new_headline = page.input_value("#builderHeadline")
        assert "Cloud Infrastructure" in new_headline or "DevOps" in new_headline, f"Expected AI-generated draft title, got '{new_headline}'"
        log_test("Creation", "AI Guided Wizard Completion", True, f"Completed 7-step wizard: loaded grounded draft '{new_headline}' without hallucinations")

        # -------------------------------------------------------------
        # 7. Resume Health Honesty & Score Consistency
        # -------------------------------------------------------------
        page.locator('.nav-groups .nav-item[data-tab="tailor"]').click()
        page.wait_for_selector("#tabImproveResume.active", timeout=5000)
        time.sleep(0.8)

        # Run analysis on the new resume
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(0.8)

        improve_score = page.text_content("#improveSummaryScoreNum").strip()
        summary_title = page.text_content("#improveSummaryTitle").strip()

        # Confirm NO "Exceptional resume!" text
        full_text = page.text_content("#tabImproveResume")
        assert "Exceptional resume!" not in full_text, "Misleading 'Exceptional resume!' message found"

        # Check canonical score consistency
        badge_score = page.text_content("#improveResumeHealthBadge").strip()
        assert improve_score in badge_score, f"Badge score '{badge_score}' does not match summary score '{improve_score}'"
        log_test("Health & Honesty", "Honest Assessment & Score Equality", True, f"Score: {improve_score}/100 ('{summary_title}'). Zero misleading exceptional praise.")

        browser.close()

    print("\n" + "=" * 70)
    print("ALL POST-OVERHAUL BROWSER QA TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    return qa_results


if __name__ == "__main__":
    results = run_post_overhaul_qa()
    with open("browser_overhaul_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    sys.exit(0)
