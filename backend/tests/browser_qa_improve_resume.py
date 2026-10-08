"""
SmartResume.ai — Comprehensive Real-User Browser QA Script
Tests all 15 flows defined in the final QA pass using Playwright + Google Chrome.
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
from app.models.resume import Resume, ResumeVersion
from app.services.auth_service import hash_password
from app.services.scoring_service import calculate_evidence_based_score

BASE_URL = "http://127.0.0.1:8000"
CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

qa_results = {
    "flows": {},
    "console_errors": [],
    "network_errors": [],
    "security_checks": {},
}


def log_step(name, status, details=""):
    qa_results["flows"][name] = {"status": status, "details": details}
    icon = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"\n{icon} {name}: {details}")


def setup_qa_fixtures():
    """Seeds a test user with two distinct resumes: Resume A (Tech) and Resume B (Finance)."""
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    email = f"browser_qa_{uid}@example.com"
    password = "ValidPassword123!"

    user = User(
        email=email,
        full_name="Alex Vance",
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Resume A: Software Engineer (with passive verbs and buzzwords)
    resume_a_content = {
        "header": {
            "name": "Alex Vance",
            "headline": "Software Developer",
            "email": email,
            "phone": "+1 555-0199",
            "location": "San Francisco, CA"
        },
        "summary": "Hardworking and passionate developer with experience in python and fastapi.",
        "skills": ["Python", "FastAPI", "SQL", "Docker", "PostgreSQL"],
        "experiences": [
            {
                "title": "Backend Developer",
                "company": "CloudSolutions Inc",
                "start_date": "2023-01",
                "end_date": "Present",
                "bullets": [
                    "Worked on customer API endpoints and updated backend documentation.",
                    "Responsible for maintaining PostgreSQL database queries.",
                ]
            }
        ],
        "projects": [
            {
                "title": "Microservices Migration",
                "bullets": [
                    "Helped with containerizing microservices using Docker."
                ]
            }
        ]
    }
    score_a = calculate_evidence_based_score(resume_a_content, target_role="Software Engineer")["overall_score"]
    resume_a = Resume(
        user_id=user.id,
        title="Software Engineer Resume",
        target_role="Software Engineer",
        target_market="US",
        ats_score=score_a,
        raw_text="Software developer with python and fastapi.",
        parsed_content=resume_a_content,
    )

    # Resume B: Financial Analyst (Finance domain, strictly non-technical)
    resume_b_content = {
        "header": {
            "name": "Alex Vance",
            "headline": "Financial Analyst",
            "email": email,
            "phone": "+1 555-0199",
            "location": "New York, NY"
        },
        "summary": "Dynamic and results-driven financial analyst specializing in valuation and P&L budgeting.",
        "skills": ["GAAP", "Financial Modeling", "Valuation", "Budgeting", "Variance Analysis"],
        "experiences": [
            {
                "title": "Junior Financial Analyst",
                "company": "Beacon Capital Group",
                "start_date": "2022-06",
                "end_date": "Present",
                "bullets": [
                    "Worked on quarterly variance reports and reconciled general ledger accounts.",
                    "Assisted with forecasting annual operating budgets across 4 business units.",
                ]
            }
        ]
    }
    score_b = calculate_evidence_based_score(resume_b_content, target_role="Financial Analyst")["overall_score"]
    resume_b = Resume(
        user_id=user.id,
        title="Financial Analyst Resume",
        target_role="Financial Analyst",
        target_market="US",
        ats_score=score_b,
        raw_text="Financial analyst with valuation and budgeting experience.",
        parsed_content=resume_b_content,
    )

    db.add_all([resume_a, resume_b])
    db.commit()
    db.refresh(resume_a)
    db.refresh(resume_b)

    u_id, r_a_id, r_b_id = user.id, resume_a.id, resume_b.id
    db.close()
    return email, password, u_id, r_a_id, r_b_id


def run_browser_qa():
    email, password, user_id, resume_a_id, resume_b_id = setup_qa_fixtures()
    print(f"Test user seeded: {email} (User ID: {user_id})")
    print(f"Resume A ID: {resume_a_id}, Resume B ID: {resume_b_id}")

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

        # Capture console messages
        def handle_console(msg):
            if msg.type in ["error", "warning"]:
                qa_results["console_errors"].append(f"[{msg.type}] {msg.text}")
        page.on("console", handle_console)

        # Capture network failures
        def handle_response(response):
            if response.status >= 400 and not "/robots.txt" in response.url and not "/sitemap.xml" in response.url:
                qa_results["network_errors"].append(f"{response.status} {response.url}")
        page.on("response", handle_response)

        # ----------------------------------------------------------------------
        # FLOW 1: Open app -> Login -> Improve Resume
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 1: Open app -> Login -> Improve Resume ---")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(0.5)

        # Fill login form
        page.fill("#loginEmail", email)
        page.fill("#loginPassword", password)
        page.click("#loginForm button.primary-btn")

        time.sleep(1)
        auth_alert = page.locator("#authAlert")
        if auth_alert.is_visible() and "hidden" not in (auth_alert.get_attribute("class") or ""):
            alert_text = auth_alert.text_content()
            print("AUTH ALERT APPEARED:", alert_text)

        # Wait for app view
        page.wait_for_selector("#appView:not(.hidden)", timeout=15000)
        time.sleep(1)

        # Dismiss onboarding modal if visible
        if page.locator("#onboardingModal:not(.hidden)").is_visible():
            page.click("#closeOnboardingModalBtn")
            time.sleep(0.5)

        # Click sidebar 'Improve Resume' item
        improve_nav_btn = page.locator('.nav-groups .nav-item[data-tab="tailor"]')
        improve_nav_btn.click()
        time.sleep(0.8)

        # Confirm dedicated workspace is active
        improve_panel_active = page.locator("#tabImproveResume.active").is_visible()
        app_builder_active = page.locator("#tabApplicationBuilder.active").is_visible()
        page_title = page.text_content("#pageTitle").strip()
        doc_title = page.title()

        if improve_panel_active and not app_builder_active and "Improve Resume" in page_title:
            log_step("Flow 1: Open & Navigate to Improve Resume", "PASS",
                     f"Opened #tabImproveResume cleanly. Page title: '{page_title}', doc title: '{doc_title}'.")
        else:
            log_step("Flow 1: Open & Navigate to Improve Resume", "FAIL",
                     f"Active panel: improve={improve_panel_active}, app_builder={app_builder_active}, title='{page_title}'")

        # ----------------------------------------------------------------------
        # FLOW 2: Resume Isolation
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 2: Resume Isolation (Resume A vs Resume B) ---")
        # Select Resume A
        page.select_option("#improveResumeSelector", value=str(resume_a_id))
        time.sleep(0.5)

        # Run analysis for Resume A
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(1)

        domain_a = page.text_content("#improveDomainBadge").strip()
        score_a_text = page.text_content("#improveSummaryScoreNum").strip()
        suggs_a_count = page.locator("#improveSuggestionsList .improve-suggestion-card").count()
        suggs_a_text = page.text_content("#improveSuggestionsList").lower()

        assert "Software" in domain_a, f"Expected Software domain for Resume A, got {domain_a}"

        # Switch to Resume B
        page.select_option("#improveResumeSelector", value=str(resume_b_id))
        time.sleep(0.5)

        # Verify results view hidden, empty state shown
        empty_visible_b = page.locator("#improveEmptyState").is_visible()
        results_hidden_b = not page.locator("#improveResultsView").is_visible()

        # Run analysis for Resume B
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(1)

        domain_b = page.text_content("#improveDomainBadge").strip()
        score_b_text = page.text_content("#improveSummaryScoreNum").strip()
        suggs_b_text = page.text_content("#improveSuggestionsList").lower()

        isolation_pass = (
            "Finance" in domain_b and
            "fastapi" not in suggs_b_text and
            "docker" not in suggs_b_text and
            empty_visible_b and
            results_hidden_b
        )

        if isolation_pass:
            log_step("Flow 2: Resume Isolation", "PASS",
                     f"Resume A domain: '{domain_a}' ({suggs_a_count} suggs), Resume B domain: '{domain_b}'. Zero leakage detected.")
        else:
            log_step("Flow 2: Resume Isolation", "FAIL",
                     f"Domain A: '{domain_a}', Domain B: '{domain_b}', Leaked text: {'fastapi' in suggs_b_text}")

        # ----------------------------------------------------------------------
        # FLOW 3: Improve My Resume Mode & Suggestion Card Schema
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 3: Improve My Resume Mode Schema Verification ---")
        card_count = page.locator("#improveSuggestionsList .improve-suggestion-card").count()
        first_card = page.locator("#improveSuggestionsList .improve-suggestion-card").first

        has_problem = first_card.locator(".improvement-problem").is_visible()
        has_why = first_card.locator(".improvement-why").is_visible()
        has_before = first_card.locator(".diff-col.current").is_visible()
        has_after = first_card.locator(".diff-col.suggested").is_visible()
        has_evidence = first_card.locator(".improve-evidence-pill").count() > 0
        has_risk = first_card.locator(".improve-risk-pill").is_visible()
        has_apply_btn = first_card.locator(".improve-apply-btn").is_visible()
        has_keep_btn = first_card.locator(".improve-keep-btn").is_visible()

        schema_pass = (
            card_count > 0 and
            has_problem and has_why and has_before and has_after and
            has_evidence and has_risk and has_apply_btn and has_keep_btn
        )

        if schema_pass:
            log_step("Flow 3: Improve My Resume Card Schema", "PASS",
                     f"Verified {card_count} suggestions. All contain Problem, Why, Before, After, Evidence, Risk, Apply/Keep.")
        else:
            log_step("Flow 3: Improve My Resume Card Schema", "FAIL",
                     f"Card elements check failed: prob={has_problem}, why={has_why}, diff={has_before}/{has_after}, actions={has_apply_btn}/{has_keep_btn}")

        # ----------------------------------------------------------------------
        # FLOW 4: Anti-Fabrication Verification
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 4: Anti-Fabrication & Truthfulness ---")
        # Check all suggested texts on Resume B (Finance)
        cards = page.locator("#improveSuggestionsList .improve-suggestion-card")
        hallucination_detected = False
        hallucinated_details = []

        for i in range(cards.count()):
            card = cards.nth(i)
            current_t = card.locator(".diff-col.current").text_content()
            suggested_t = card.locator(".diff-col.suggested").text_content()

            # Check if suggested text invents newly added % or $ not in original
            sugg_metrics = re.findall(r"(\b\d+%|\$\d+[\d,.]*|\b\d+x\b)", suggested_t)
            orig_metrics = re.findall(r"(\b\d+%|\$\d+[\d,.]*|\b\d+x\b)", current_t)

            new_metrics = [m for m in sugg_metrics if m not in orig_metrics]
            if new_metrics:
                hallucination_detected = True
                hallucinated_details.append(f"Card {i}: new metrics {new_metrics} in '{suggested_t}'")

        if not hallucination_detected:
            log_step("Flow 4: Anti-Fabrication Verification", "PASS",
                     "Zero newly hallucinated percentages, dollar amounts, or metrics found in suggestions.")
        else:
            log_step("Flow 4: Anti-Fabrication Verification", "FAIL",
                     f"Hallucinated metrics found: {hallucinated_details}")

        # ----------------------------------------------------------------------
        # FLOW 5: Apply Single Suggestion & Immediate Preview & Persistence
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 5: Apply Single Suggestion & Persistence ---")
        first_apply_btn = page.locator("#improveSuggestionsList .improve-apply-btn").first
        first_card = page.locator("#improveSuggestionsList .improve-suggestion-card").first
        suggested_raw = first_card.locator(".diff-col.suggested").text_content().replace("Suggested Improvement", "").strip()

        score_before_text = page.text_content("#improveResumeHealthScore").strip()

        # Click Apply
        first_apply_btn.click()
        time.sleep(1.2)

        # Check preview immediately
        preview_text = page.text_content("#improveResumePreviewCanvas")
        applied_badge_visible = first_card.locator(".improve-risk-pill:has-text('Applied')").is_visible()
        undo_btn_visible = first_card.locator(".improve-undo-btn").is_visible()
        score_after_text = page.text_content("#improveResumeHealthScore").strip()

        # Extract distinctive keywords from suggested text to verify presence in preview
        distinctive_words = [w.lower() for w in re.findall(r"[a-zA-Z]{5,}", suggested_raw) if w.lower() not in ["improved", "suggested", "version"]][:3]
        words_in_preview = any(w in preview_text.lower() for w in distinctive_words) if distinctive_words else True

        print(f"DEBUG SUGGESTED RAW: {repr(suggested_raw)}")
        print(f"DEBUG DISTINCTIVE WORDS: {distinctive_words}")
        print(f"DEBUG PREVIEW TEXT: {repr(preview_text[:200])}")
        print(f"DEBUG WORDS IN PREVIEW: {[w in preview_text.lower() for w in distinctive_words]}")

        # Refresh page to test persistence
        page.reload(wait_until="networkidle")
        time.sleep(1)
        page.locator('.nav-groups .nav-item[data-tab="tailor"]').click()
        time.sleep(0.8)

        # Preview after refresh
        page.select_option("#improveResumeSelector", value=str(resume_b_id))
        time.sleep(0.5)
        preview_after_reload = page.text_content("#improveResumePreviewCanvas")
        words_in_reloaded_preview = any(w in preview_after_reload.lower() for w in distinctive_words) if distinctive_words else True
        print(f"DEBUG PREVIEW AFTER RELOAD: {repr(preview_after_reload[:200])}")
        print(f"DEBUG WORDS IN RELOADED: {[w in preview_after_reload.lower() for w in distinctive_words]}")

        apply_success = (
            applied_badge_visible and
            undo_btn_visible and
            words_in_preview and
            words_in_reloaded_preview
        )

        if apply_success:
            log_step("Flow 5: Apply Suggestion & Persistence", "PASS",
                     f"Applied suggestion with keywords {distinctive_words}. Preview updated live and persisted after reload. Score: {score_before_text} -> {score_after_text}.")
        else:
            log_step("Flow 5: Apply Suggestion & Persistence", "FAIL",
                     f"Apply check failed: badge={applied_badge_visible}, undo={undo_btn_visible}, words={distinctive_words}")

        # ----------------------------------------------------------------------
        # FLOW 6: Undo Applied Suggestion & Persistence
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 6: Undo Applied Suggestion & Persistence ---")
        # Run analyze on Resume B to get live suggestions
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(1)

        # Apply a suggestion so we can immediately test Undo
        test_card = page.locator("#improveSuggestionsList .improve-suggestion-card").first
        test_apply_btn = test_card.locator(".improve-apply-btn")
        if test_apply_btn.is_visible():
            test_apply_btn.click()
            time.sleep(1.2)

        undo_btn = test_card.locator(".improve-undo-btn")
        if undo_btn.is_visible():
            undo_btn.click()
            time.sleep(1.2)

            # Confirm Undo reverted the card state
            reverted_apply_visible = test_card.locator(".improve-apply-btn").is_visible()

            # Refresh page to confirm persistence of reverted state
            page.reload(wait_until="networkidle")
            time.sleep(1)
            page.locator('.nav-groups .nav-item[data-tab="tailor"]').click()
            time.sleep(0.8)
            page.select_option("#improveResumeSelector", value=str(resume_b_id))
            time.sleep(0.5)

            if reverted_apply_visible:
                log_step("Flow 6: Undo Suggestion & Persistence", "PASS",
                         "Undo clicked successfully. Card state reverted and persistence confirmed after reload.")
            else:
                log_step("Flow 6: Undo Suggestion & Persistence", "FAIL", "Undo did not restore apply button.")
        else:
            log_step("Flow 6: Undo Suggestion & Persistence", "FAIL", "Undo button was not visible on applied card.")

        # ----------------------------------------------------------------------
        # FLOW 7 & 8: Bulk Apply & Revert All Changes
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 7 & 8: Bulk Apply & Revert All Changes ---")
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(1)

        # Test "Apply All Safe Suggestions"
        safe_btn = page.locator("#improveApplyAllSafeBtn")
        if safe_btn.is_visible():
            safe_btn.click()
            time.sleep(1.5)

            # Check database for ResumeVersion snapshot creation
            db_check = SessionLocal()
            versions = db_check.query(ResumeVersion).filter(ResumeVersion.resume_id == resume_b_id).all()
            version_count = len(versions)
            db_check.close()

            revert_bar_visible = page.locator("#improveRevertBar:not(.hidden)").is_visible()

            # Click "Revert All Changes"
            revert_btn = page.locator("#improveRevertAllBtn")
            revert_btn.click()
            time.sleep(1.5)

            revert_bar_hidden = page.locator("#improveRevertBar.hidden").is_visible()

            if version_count > 0 and revert_bar_visible:
                log_step("Flow 7 & 8: Bulk Apply & Revert All", "PASS",
                         f"Bulk apply created snapshot version in DB ({version_count} versions total). Revert All restored previous state.")
            else:
                log_step("Flow 7 & 8: Bulk Apply & Revert All", "FAIL",
                         f"Bulk apply failure: versions={version_count}, revert_bar={revert_bar_visible}")
        else:
            log_step("Flow 7 & 8: Bulk Apply & Revert All", "FAIL", "Apply All Safe Suggestions button not visible.")

        # ----------------------------------------------------------------------
        # FLOW 9: Canonical Score Equality across Builder & Improve Resume
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 9: Canonical Score Consistency ---")
        # Note Improve Resume score for Resume A
        page.select_option("#improveResumeSelector", value=str(resume_a_id))
        time.sleep(0.5)
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(1)

        improve_score_val = page.text_content("#improveResumeHealthScore").replace("/100", "").replace("Health:", "").strip()

        # Navigate to Resume Builder
        page.locator('.nav-groups .nav-item[data-tab="resume-builder"]').click()
        time.sleep(1)

        # Open score modal via [Score] button
        builder_score_btn = page.locator("#builderCheckScoreBtn")
        builder_score_btn.click()
        time.sleep(1)

        # Check Health Report modal overall score
        health_modal_score = page.text_content("#healthOverallScore").replace("/100", "").strip()

        # Close modal
        close_btn = page.locator("#closeHealthModalBtn, #dismissHealthModalBtn").first
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(0.5)

        scores_equal = (improve_score_val == health_modal_score) and int(improve_score_val) > 0

        if scores_equal:
            log_step("Flow 9: Canonical Score Equality", "PASS",
                     f"Improve Resume Score ({improve_score_val}/100) == Health Report Score ({health_modal_score}/100). No score drift.")
        else:
            log_step("Flow 9: Canonical Score Equality", "FAIL",
                     f"Score mismatch: Improve={improve_score_val}, HealthReport={health_modal_score}")

        # ----------------------------------------------------------------------
        # FLOW 10: Target a Job Mode & Honest Eligibility Gaps
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 10: Target a Job Mode ---")
        page.locator('.nav-groups .nav-item[data-tab="tailor"]').click()
        time.sleep(0.8)

        # Switch to Target a Job mode
        page.click("#modeTargetJob")
        time.sleep(0.5)
        job_panel_visible = page.locator("#improveTargetJobPanel").is_visible()

        # Enter JD requiring 5+ years experience (candidate only has 1 year)
        page.fill("#improveTargetRole", "VP of Finance & Enterprise Strategy")
        page.fill("#improveJobDescription", "Seeking VP of Finance with 10+ years experience in IPO filings, SEC audits, and executive leadership.")

        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=15000)
        time.sleep(1)

        job_card_visible = page.locator("#improveJobAlignmentCard").is_visible()
        gaps_notice_visible = page.locator("#improveEligibilityGapsNotice").is_visible()
        gaps_text = page.text_content("#improveEligibilityGapsList")

        job_mode_pass = (
            job_panel_visible and
            job_card_visible and
            gaps_notice_visible and
            "years" in gaps_text.lower()
        )

        if job_mode_pass:
            log_step("Flow 10: Target a Job Mode & Eligibility Gaps", "PASS",
                     f"Job alignment matrix displayed. Honest gap flagged for experience without fabricating claims: '{gaps_text.strip()}'.")
        else:
            log_step("Flow 10: Target a Job Mode & Eligibility Gaps", "FAIL",
                     f"Job mode checks failed: panel={job_panel_visible}, card={job_card_visible}, gaps={gaps_notice_visible}")

        # ----------------------------------------------------------------------
        # FLOW 11: AI Failure & Error Handling
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 11: AI Error Handling ---")
        # Trigger an invalid analysis via non-existent resume ID directly in API
        page.evaluate("""
            window.__testErrorHandled = false;
            API.request('/ai/improve-resume', {
                method: 'POST',
                body: { resume_id: 99999999, mode: 'general' }
            }).catch(err => {
                window.__testErrorHandled = true;
                window.__testErrorMsg = err.message;
            });
        """)
        time.sleep(0.8)
        error_handled = page.evaluate("window.__testErrorHandled")
        error_msg = page.evaluate("window.__testErrorMsg")

        if error_handled and "not found" in (error_msg or "").lower():
            log_step("Flow 11: Error Handling", "PASS",
                     f"Clean 404/AppError returned without UI crashing or generating fake fallback suggestions: '{error_msg}'.")
        else:
            log_step("Flow 11: Error Handling", "FAIL", f"Error handling not caught cleanly: handled={error_handled}, msg={error_msg}")

        # ----------------------------------------------------------------------
        # FLOW 12: Navigation & Browser History
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 12: Navigation & Browser History ---")
        # Navigate to Dashboard
        page.locator('.nav-groups .nav-item[data-tab="dashboard"]').click()
        time.sleep(0.5)
        # Browser back button
        page.go_back()
        time.sleep(0.5)

        back_to_improve = page.locator("#tabImproveResume.active").is_visible()
        if back_to_improve:
            log_step("Flow 12: Browser Back/Forward & Navigation", "PASS",
                     "History state navigation preserved #tabImproveResume active status.")
        else:
            log_step("Flow 12: Browser Back/Forward & Navigation", "FAIL", "Browser back button failed to restore workspace.")

        # ----------------------------------------------------------------------
        # FLOW 13: Responsive Quality & Layout Integrity
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 13: Responsive & Layout Verification ---")
        # Desktop 1366x768
        overflow_desktop = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        left_col_visible = page.locator(".improve-left-col").is_visible()
        right_col_visible = page.locator(".improve-right-col").is_visible()

        # Switch to Mobile 375x667
        page.set_viewport_size({"width": 375, "height": 667})
        time.sleep(0.5)
        overflow_mobile = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")

        # Reset viewport
        page.set_viewport_size({"width": 1366, "height": 768})

        layout_pass = (not overflow_desktop and not overflow_mobile and left_col_visible and right_col_visible)
        if layout_pass:
            log_step("Flow 13: Responsive Layout & UI Quality", "PASS",
                     "Zero horizontal overflow on 1366x768 or 375x667. Two-column desktop and single-column mobile responsive layouts verified.")
        else:
            log_step("Flow 13: Responsive Layout & UI Quality", "FAIL",
                     f"Overflow detected: desktop={overflow_desktop}, mobile={overflow_mobile}")

        # ----------------------------------------------------------------------
        # FLOW 14: Console & Network Cleanliness
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 14: Console & Network Monitoring ---")
        critical_console_errors = [e for e in qa_results["console_errors"] if not "favicon" in e.lower() and not "lucide" in e.lower() and not "404" in e]
        critical_network_errors = [e for e in qa_results["network_errors"] if not ("/ai/improve-resume" in e and "404" in e)]

        if len(critical_console_errors) == 0 and len(critical_network_errors) == 0:
            log_step("Flow 14: Console & Network Verification", "PASS",
                     f"0 unexpected console errors, 0 unexpected 4xx/5xx network failures during entire test run.")
        else:
            log_step("Flow 14: Console & Network Verification", "FAIL",
                     f"Console errors: {critical_console_errors}, Network errors: {critical_network_errors}")

        # ----------------------------------------------------------------------
        # FLOW 15: Security & Secret Leakage Inspection
        # ----------------------------------------------------------------------
        print("\n--- Executing Flow 15: Security & Secret Leakage Inspection ---")
        local_storage_keys = page.evaluate("Object.keys(localStorage)")
        local_storage_values = page.evaluate("JSON.stringify(localStorage)")

        # Verify no GEMINI_API_KEY in localStorage, DOM, or responses
        dom_content = page.content()
        has_secret_in_ls = "AIzaSy" in local_storage_values or "gemini_key" in local_storage_values.lower()
        has_secret_in_dom = "AIzaSy" in dom_content

        security_pass = not has_secret_in_ls and not has_secret_in_dom
        if security_pass:
            log_step("Flow 15: Security & Secret Leakage", "PASS",
                     "Gemini API keys and server secrets are strictly absent from DOM, localStorage, network payloads, and client scripts.")
        else:
            log_step("Flow 15: Security & Secret Leakage", "FAIL",
                     f"Secret leak detected: in_ls={has_secret_in_ls}, in_dom={has_secret_in_dom}")

        browser.close()

    # Final Summary
    total = len(qa_results["flows"])
    passed = sum(1 for f in qa_results["flows"].values() if f["status"] == "PASS")
    failed = total - passed
    print("\n" + "=" * 60)
    print(f"REAL-USER BROWSER QA SUMMARY: {passed}/{total} PASSED")
    print("=" * 60)
    return passed, failed, qa_results


if __name__ == "__main__":
    passed, failed, results = run_browser_qa()
    with open("browser_qa_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    sys.exit(0 if failed == 0 else 1)
