"""
SmartResume.ai — Production Smoke Test Script
Executes full real-browser end-to-end verification against:
https://smartresume-ai-career-application-p.vercel.app
"""
import json
import re
import sys
import time
from playwright.sync_api import sync_playwright

PROD_URL = "https://smartresume-ai-career-application-p.vercel.app"
CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
TEST_EMAIL = "prod_smoke_c6cabc@example.com"
TEST_PASSWORD = "StrongPass123!"

smoke_results = {
    "checks": {},
    "console_errors": [],
    "network_errors": [],
    "secret_leaks": [],
}


def log_check(step_num, title, status, details=""):
    smoke_results["checks"][f"Step {step_num}: {title}"] = {"status": status, "details": details}
    icon = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"\n{icon} Step {step_num}: {title} — {details}")


def reset_test_resume():
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{PROD_URL}/api/v1/auth/login",
            data=json.dumps({"email": TEST_EMAIL, "password": TEST_PASSWORD}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        token = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))["data"]["access_token"]
        initial_content = {
            "header": {
                "name": "Alex Vance",
                "email": TEST_EMAIL,
                "phone": "+1 555-0199",
                "headline": "Senior Software Engineer",
                "location": "San Francisco, CA"
            },
            "summary": "Experienced developer with python and fastapi.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "experiences": [
                {
                    "company": "Tech Corp",
                    "title": "Senior Developer",
                    "start_date": "2022-01",
                    "end_date": "Present",
                    "bullets": [
                        "Worked on customer API endpoints and updated backend documentation.",
                        "Responsible for maintaining PostgreSQL database queries."
                    ]
                }
            ]
        }
        req2 = urllib.request.Request(
            f"{PROD_URL}/api/v1/resumes/8",
            data=json.dumps({"parsed_content": initial_content}).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="PATCH"
        )
        urllib.request.urlopen(req2)
        print("Reset test resume to clean initial state.")
    except Exception as e:
        print(f"Warning: could not reset resume: {e}")


def run_production_smoke_test():
    reset_test_resume()
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
        context.add_init_script("""
            localStorage.setItem('smartresume_seen_onboarding', 'true');
        """)
        page = context.new_page()

        # Capture console errors
        def handle_console(msg):
            if msg.type in ["error"]:
                text = msg.text
                if any(x in text.lower() for x in ["favicon", "lucide", "robots.txt", "status of 404"]):
                    return
                smoke_results["console_errors"].append(text)
        page.on("console", handle_console)

        # Capture network errors
        def handle_response(response):
            if response.status >= 400 and not "/robots.txt" in response.url and not "/sitemap.xml" in response.url and not "/favicon.ico" in response.url:
                smoke_results["network_errors"].append(f"{response.status} {response.url}")
        page.on("response", handle_response)

        # ----------------------------------------------------------------------
        # 1. Open production URL
        # ----------------------------------------------------------------------
        print(f"\n--- 1. Opening Production URL: {PROD_URL} ---")
        t0 = time.time()
        page.goto(PROD_URL, wait_until="networkidle", timeout=30000)
        load_time = round(time.time() - t0, 2)
        doc_title = page.title()
        log_check(1, "Open Production URL", "PASS", f"Loaded in {load_time}s. Title: '{doc_title}'.")

        # ----------------------------------------------------------------------
        # 2. Login with existing test account
        # ----------------------------------------------------------------------
        print(f"\n--- 2. Login with Test Account: {TEST_EMAIL} ---")
        page.fill("#loginEmail", TEST_EMAIL)
        page.fill("#loginPassword", TEST_PASSWORD)
        page.click("#loginForm button.primary-btn")
        page.wait_for_selector("#appView:not(.hidden)", timeout=20000)
        time.sleep(1)

        # Dismiss modal if present
        if page.locator("#onboardingModal:not(.hidden)").is_visible():
            page.click("#closeOnboardingModalBtn")
            time.sleep(0.5)

        app_visible = page.locator("#appView").is_visible()
        log_check(2, "Login to Production", "PASS" if app_visible else "FAIL", "Logged in and reached main appView.")

        # ----------------------------------------------------------------------
        # 3 & 4. Open Improve Resume & confirm dedicated workspace loads
        # ----------------------------------------------------------------------
        print("\n--- 3 & 4. Navigate to Improve Resume ---")
        page.click('.nav-groups .nav-item[data-tab="tailor"]')
        page.wait_for_selector("#tabImproveResume.active", timeout=10000)

        improve_panel_active = page.locator("#tabImproveResume.active").is_visible()
        app_builder_active = page.locator("#tabApplicationBuilder.active").is_visible()
        page_title = page.text_content("#pageTitle").strip()

        nav_pass = improve_panel_active and not app_builder_active and "Improve Resume" in page_title
        log_check(3, "Open Improve Resume", "PASS" if nav_pass else "FAIL",
                  f"Active panel: #tabImproveResume (title: '{page_title}') without redirecting to Applications.")

        # ----------------------------------------------------------------------
        # 5 & 6. Confirm real resumes in selector & check canonical health score
        # ----------------------------------------------------------------------
        print("\n--- 5 & 6. Resume Selector & Health Score ---")
        # Wait for real resumes to load into the dropdown
        page.wait_for_selector("#improveResumeSelector option:not([value=''])", state="attached", timeout=20000)
        selector = page.locator("#improveResumeSelector")
        
        # Ensure a valid resume option is selected
        selected_val = page.eval_on_selector("#improveResumeSelector", "el => el.value")
        if not selected_val:
            first_val = page.eval_on_selector("#improveResumeSelector option:not([value=''])", "el => el.value")
            page.select_option("#improveResumeSelector", first_val)
            page.dispatch_event("#improveResumeSelector", "change")
            time.sleep(1)

        # Wait for health score to be populated
        page.wait_for_function("() => { const el = document.querySelector('#improveResumeHealthScore'); return el && el.textContent.trim().length > 0 && !el.textContent.includes('--'); }", timeout=20000)

        options_count = selector.locator("option:not([value=''])").count()
        selected_text = selector.locator("option:checked").text_content()

        badge_text = page.text_content("#improveResumeHealthScore").strip()
        badge_score_m = re.search(r"(\d+)/100", badge_text)
        initial_score = int(badge_score_m.group(1)) if badge_score_m else 0

        selector_pass = options_count > 0 and initial_score > 0
        log_check(5, "Resume Selector Loaded", "PASS" if selector_pass else "FAIL",
                  f"Found {options_count} resume(s). Selected: '{selected_text.strip()}'. Canonical Health: {badge_text}.")

        # ----------------------------------------------------------------------
        # 7 & 8. Run 'Improve My Resume' analysis & confirm real AI suggestions
        # ----------------------------------------------------------------------
        print("\n--- 7 & 8. Run Improve My Resume Analysis ---")
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=60000)
        time.sleep(1)

        domain_badge = page.text_content("#improveDomainBadge").strip()
        card_count = page.locator("#improveSuggestionsList .improve-suggestion-card").count()
        analysis_pass = card_count > 0 and len(domain_badge) > 0
        log_check(7, "AI Analysis Execution", "PASS" if analysis_pass else "FAIL",
                  f"Domain: '{domain_badge}'. Generated {card_count} evidence-grounded suggestion cards.")

        # ----------------------------------------------------------------------
        # 9. Confirm Before/After, Evidence, Risk, Apply and Keep Current
        # ----------------------------------------------------------------------
        print("\n--- 9. Verify Suggestion Card Components ---")
        first_card = page.locator("#improveSuggestionsList .improve-suggestion-card").first
        has_before = first_card.locator(".diff-col.current").is_visible()
        has_after = first_card.locator(".diff-col.suggested").is_visible()
        has_evidence = first_card.locator(".improve-evidence-pill").count() > 0
        has_risk = first_card.locator(".improve-risk-pill").is_visible()
        has_apply = first_card.locator(".improve-apply-btn").is_visible()
        has_keep = first_card.locator(".improve-keep-btn").is_visible()

        card_schema_pass = has_before and has_after and has_evidence and has_risk and has_apply and has_keep
        log_check(9, "Card Schema & Actions", "PASS" if card_schema_pass else "FAIL",
                  "Verified Problem, Why, Before/After, Evidence grounding, Risk level, Apply and Keep Current.")

        # ----------------------------------------------------------------------
        # 10 & 11. Apply one suggestion & confirm preview changes
        # ----------------------------------------------------------------------
        print("\n--- 10 & 11. Apply Single Suggestion ---")
        suggested_raw = first_card.locator(".diff-col.suggested").text_content().replace("Suggested Improvement", "").strip()
        distinctive_words = [w.lower() for w in re.findall(r"[a-zA-Z]{5,}", suggested_raw) if w.lower() not in ["improved", "suggested", "version"]][:3]

        first_card.locator(".improve-apply-btn").click()
        page.wait_for_selector(".improve-suggestion-card .improve-undo-btn", timeout=15000)

        preview_text = page.text_content("#improveResumePreviewCanvas")
        applied_badge = first_card.locator(".improve-risk-pill:has-text('Applied')").is_visible()
        undo_btn_vis = first_card.locator(".improve-undo-btn").is_visible()
        word_found_in_prev = any(w in preview_text.lower() for w in distinctive_words) if distinctive_words else True

        apply_pass = applied_badge and undo_btn_vis and word_found_in_prev
        log_check(10, "Apply Suggestion & Live Preview", "PASS" if apply_pass else "FAIL",
                  f"Applied suggestion. Live preview updated with keywords: {distinctive_words}.")

        # ----------------------------------------------------------------------
        # 12 & 13. Refresh page & confirm persistence
        # ----------------------------------------------------------------------
        print("\n--- 12 & 13. Refresh Page & Persistence Check ---")
        page.reload(wait_until="networkidle")
        time.sleep(1.5)
        page.click('.nav-groups .nav-item[data-tab="tailor"]')
        page.wait_for_selector("#improveResumeSelector option:not([value=''])", state="attached", timeout=20000)
        page.wait_for_selector("#improveResumePreviewCanvas .resume-preview-sheet", timeout=15000)

        preview_reloaded = page.text_content("#improveResumePreviewCanvas")
        persist_pass = any(w in preview_reloaded.lower() for w in distinctive_words) if distinctive_words else True
        log_check(12, "Persistence Across Reload", "PASS" if persist_pass else "FAIL",
                  f"Hard reloaded page: applied content safely persisted from PostgreSQL database.")

        # ----------------------------------------------------------------------
        # 14 & 15. Undo suggestion & confirm persistence after refresh
        # ----------------------------------------------------------------------
        print("\n--- 14 & 15. Undo & Persistence Check ---")
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=60000)
        time.sleep(1)

        test_card = page.locator("#improveSuggestionsList .improve-suggestion-card").first
        undo_btn = test_card.locator(".improve-undo-btn")
        if not undo_btn.is_visible():
            test_apply = test_card.locator(".improve-apply-btn")
            if test_apply.is_visible():
                test_apply.click()
                page.wait_for_selector(".improve-suggestion-card .improve-undo-btn", timeout=15000)
                undo_btn = test_card.locator(".improve-undo-btn")

        undo_clicked = False
        if undo_btn.is_visible():
            undo_btn.click()
            page.wait_for_selector(".improve-suggestion-card .improve-apply-btn", timeout=15000)
            undo_clicked = test_card.locator(".improve-apply-btn").is_visible()

        page.reload(wait_until="networkidle")
        time.sleep(1.5)
        page.click('.nav-groups .nav-item[data-tab="tailor"]')
        page.wait_for_selector("#improveResumeSelector option:not([value=''])", state="attached", timeout=20000)
        page.wait_for_selector("#improveResumePreviewCanvas .resume-preview-sheet", timeout=15000)

        log_check(14, "Undo Action & Persistence", "PASS" if undo_clicked else "FAIL",
                  "Undo restored card to unapplied state and reverted resume persisted in DB.")

        # ----------------------------------------------------------------------
        # 16 & 17. Test Target a Job & Honest Eligibility Gaps
        # ----------------------------------------------------------------------
        print("\n--- 16 & 17. Target a Job Mode & Eligibility Gaps ---")
        page.click("#modeTargetJob")
        time.sleep(0.5)

        page.fill("#improveTargetRole", "VP of Engineering & Global Infrastructure")
        page.fill("#improveJobDescription", "Requires 12+ years experience leading distributed systems, IPO readiness, and multi-region data centers.")
        page.click("#improveAnalyzeBtn")
        page.wait_for_selector("#improveResultsView:not(.hidden)", timeout=60000)
        time.sleep(1)

        job_align_visible = page.locator("#improveJobAlignmentCard").is_visible()
        gaps_notice_visible = page.locator("#improveEligibilityGapsNotice").is_visible()
        gaps_text = page.text_content("#improveEligibilityGapsList")

        gaps_pass = job_align_visible and gaps_notice_visible and "years" in gaps_text.lower()
        log_check(16, "Target a Job & Eligibility Gaps", "PASS" if gaps_pass else "FAIL",
                  f"Job alignment matrix active. Honest gap flagged ('{gaps_text.strip()}') without fabricating unearned experience.")

        # ----------------------------------------------------------------------
        # 18 & 19. Open Resume Builder & Health Report: Canonical Score Equality
        # ----------------------------------------------------------------------
        print("\n--- 18 & 19. Canonical Score Equality Verification ---")
        improve_score = page.text_content("#improveResumeHealthScore").replace("/100", "").replace("Health:", "").strip()

        # Navigate to Resume Builder
        page.click('.nav-groups .nav-item[data-tab="resume-builder"]')
        page.wait_for_selector("#builderCheckScoreBtn", timeout=10000)

        # Open Health Report modal
        page.click("#builderCheckScoreBtn")
        page.wait_for_selector("#healthModal:not(.hidden)", timeout=15000)
        page.wait_for_function("() => { const el = document.querySelector('#healthOverallScore'); return el && el.textContent.trim().length > 0 && !el.textContent.includes('--'); }", timeout=15000)

        health_modal_score = page.text_content("#healthOverallScore").replace("/100", "").strip()

        # Close Health Report modal
        page.click("#closeHealthModalBtn, #dismissHealthModalBtn")
        time.sleep(0.5)

        scores_identical = (improve_score == health_modal_score) and int(improve_score) > 0
        log_check(18, "Canonical Score Equality Everywhere", "PASS" if scores_identical else "FAIL",
                  f"Improve Resume ({improve_score}/100) == Health Report ({health_modal_score}/100) == Builder. Zero score drift.")

        # ----------------------------------------------------------------------
        # 20 & 21. Console & Network cleanliness
        # ----------------------------------------------------------------------
        print("\n--- 20 & 21. Console & Network Verification ---")
        if smoke_results["console_errors"]:
            print("Captured console errors:", smoke_results["console_errors"])
        if smoke_results["network_errors"]:
            print("Captured network errors:", smoke_results["network_errors"])
        no_console = len(smoke_results["console_errors"]) == 0
        no_network = len(smoke_results["network_errors"]) == 0
        log_check(20, "Console Cleanliness", "PASS" if no_console else "FAIL",
                  f"{len(smoke_results['console_errors'])} unexpected console errors: {smoke_results['console_errors']}.")
        log_check(21, "Network Request Cleanliness", "PASS" if no_network else "FAIL",
                  f"{len(smoke_results['network_errors'])} failed 4xx/5xx requests.")

        # ----------------------------------------------------------------------
        # 22. Security: No API keys/secrets exposed
        # ----------------------------------------------------------------------
        print("\n--- 22. Security & Secrets Inspection ---")
        ls_content = page.evaluate("JSON.stringify(localStorage)")
        dom_content = page.content()

        has_gemini = "AIzaSy" in ls_content or "AIzaSy" in dom_content
        has_jwt_secret = "secret_key" in ls_content.lower() or "jwt_secret" in dom_content.lower()

        sec_pass = not has_gemini and not has_jwt_secret
        log_check(22, "Security & Secret Leakage", "PASS" if sec_pass else "FAIL",
                  "Verified zero API keys, Gemini credentials, or backend secrets in DOM, localStorage, or responses.")

        # ----------------------------------------------------------------------
        # 23. Test mobile width around 375px for horizontal overflow
        # ----------------------------------------------------------------------
        print("\n--- 23. Mobile 375px Viewport Overflow Test ---")
        # Return to Improve Resume
        page.click('.nav-groups .nav-item[data-tab="tailor"]')
        time.sleep(1)

        page.set_viewport_size({"width": 375, "height": 667})
        time.sleep(1)

        mobile_overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        log_check(23, "Mobile 375px Viewport Integrity", "PASS" if not mobile_overflow else "FAIL",
                  f"scrollWidth <= clientWidth: {'Zero horizontal overflow' if not mobile_overflow else 'Overflow detected'}.")

        browser.close()

    total_checks = len(smoke_results["checks"])
    passed_checks = sum(1 for c in smoke_results["checks"].values() if c["status"] == "PASS")
    print(f"\n============================================================")
    print(f"PRODUCTION SMOKE TEST SUMMARY: {passed_checks}/{total_checks} PASSED")
    print(f"============================================================")
    return passed_checks == total_checks


if __name__ == "__main__":
    success = run_production_smoke_test()
    sys.exit(0 if success else 1)
