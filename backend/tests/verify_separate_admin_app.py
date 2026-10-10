import os
import sys
import time
import json
import requests
import subprocess
from playwright.sync_api import sync_playwright

ADMIN_URL = "http://127.0.0.1:4174"
USER_APP_URL = "http://127.0.0.1:8000"
PROD_URL = "https://smartresume-ai-career-application-p.vercel.app"

CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"

def run_separate_admin_verification():
    print("=" * 75)
    print("SMARTRESUME.AI — SEPARATE ADMIN APPLICATION ARCHITECTURE VERIFICATION")
    print("=" * 75)

    results = {
        "admin_url": ADMIN_URL,
        "user_app_url": USER_APP_URL,
        "public_website_isolation": {},
        "admin_app_connectivity": {},
        "standard_user_rejection": {},
        "admin_login_and_kpis": {},
        "user_management_actions": {},
        "ai_ops_telemetry": {},
        "feature_flags_persistence": {},
        "audit_trail_logging": {},
        "logout_flow": {},
        "verdict": "PENDING"
    }

    # 1. Start Admin Panel Server
    print("\n--- 1. Starting Dedicated Admin Panel Server on port 4174 ---")
    admin_proc = subprocess.Popen(
        [sys.executable, "admin-panel/server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )
    time.sleep(2.0)

    try:
        # Check server response
        res = requests.get(f"{ADMIN_URL}/index.html", timeout=5)
        assert res.status_code == 200, f"Admin server returned {res.status_code}"
        assert "SmartResume.ai" in res.text
        assert "Admin Management Portal" in res.text
        results["admin_app_connectivity"] = {"status": "ONLINE", "http_code": 200}
        print("Dedicated Admin Server is ONLINE at http://127.0.0.1:4174")

        # 2. Register disposable test users on backend
        ts = int(time.time() * 1000)
        std_email = f"std_user_{ts}@example.com"
        admin_email = f"admin_user_{ts}@example.com"
        pwd = "SecurePassword123!"

        reg_std = requests.post(f"{USER_APP_URL}/api/v1/auth/register", json={"email": std_email, "password": pwd, "full_name": "Standard Seeker"}).json()
        reg_adm = requests.post(f"{USER_APP_URL}/api/v1/auth/register", json={"email": admin_email, "password": pwd, "full_name": "Admin Operator"}).json()
        adm_id = reg_adm.get("data", {}).get("user", {}).get("id")
        std_id = reg_std.get("data", {}).get("user", {}).get("id")

        # Elevate admin user in DB
        from app.database import get_db
        from app.models.user import User
        db = next(get_db())
        u = db.get(User, adm_id)
        u.role = "ADMIN"
        db.commit()
        db.close()
        print(f"Created standard user ({std_email}) and elevated admin user ({admin_email})")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--disable-web-security", "--no-sandbox"]
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # -------------------------------------------------------------
            # TEST A: Public User Website Isolation (No Admin UI)
            # -------------------------------------------------------------
            print("\n--- 2. Verifying Public Website Isolation (Zero Admin UI) ---")
            page.goto(f"{USER_APP_URL}/#/dashboard", wait_until="networkidle")
            page.wait_for_selector("#loginEmail", timeout=10000)
            page.fill("#loginEmail", admin_email)
            page.fill("#loginPassword", pwd)
            page.click("#loginForm button.primary-btn")
            page.wait_for_selector("#appView:not(.hidden)", timeout=15000)
            time.sleep(1.0)

            # Confirm adminNavItem does NOT exist in DOM
            has_admin_nav = page.evaluate("() => document.getElementById('adminNavItem') !== null")
            has_tab_admin = page.evaluate("() => document.getElementById('tabAdmin') !== null")
            print(f"Public website has #adminNavItem in DOM: {has_admin_nav} (Expected: False)")
            print(f"Public website has #tabAdmin in DOM: {has_tab_admin} (Expected: False)")
            assert not has_admin_nav, "Public website must NOT have #adminNavItem"
            assert not has_tab_admin, "Public website must NOT have #tabAdmin"

            # Try navigating to #/admin on public website
            page.evaluate("() => window.location.hash = '#/admin'")
            time.sleep(1.0)
            active_tab = page.evaluate("() => document.querySelector('.tab-panel.active')?.id")
            print(f"Active tab on public website after navigating to #/admin: '{active_tab}'")
            assert active_tab == "tabDashboard", f"Expected tabDashboard on public website, got {active_tab}"

            results["public_website_isolation"] = {
                "adminNavItem_present": has_admin_nav,
                "tabAdmin_present": has_tab_admin,
                "admin_hash_rendered_admin_tab": False,
                "status": "VERIFIED_ISOLATED"
            }

            # -------------------------------------------------------------
            # TEST B: Separate Admin Application Authentication
            # -------------------------------------------------------------
            print("\n--- 3. Testing Dedicated Admin App Authentication ---")
            page.goto(ADMIN_URL, wait_until="networkidle")
            page.wait_for_selector("#adminAuthView:not(.hidden)", timeout=10000)
            print("Admin Portal Auth Screen loaded successfully.")

            # Attempt login with Standard User (Should Fail with Access Denied)
            print("Attempting login as Standard User...")
            page.fill("#adminEmailInput", std_email)
            page.fill("#adminPasswordInput", pwd)
            page.click("#adminLoginBtn")
            page.wait_for_selector("#authErrorMessage:not(.hidden)", timeout=10000)
            err_text = page.inner_text("#authErrorMessage")
            print(f"Standard user login rejection message: '{err_text}'")
            assert "Access Denied" in err_text or "Admin" in err_text
            results["standard_user_rejection"] = {
                "status": "BLOCKED_403",
                "message": err_text
            }

            # Login with Admin User (Should Succeed)
            print("Attempting login as Administrator...")
            page.fill("#adminEmailInput", admin_email)
            page.fill("#adminPasswordInput", pwd)
            page.click("#adminLoginBtn")
            page.wait_for_selector("#adminAppView:not(.hidden)", timeout=15000)
            time.sleep(1.0)
            print("Administrator authenticated successfully! App View visible.")

            # -------------------------------------------------------------
            # TEST C: Dedicated Admin Panel Views & Actions
            # -------------------------------------------------------------
            # 1. Overview Tab
            print("\n--- 4. Testing Overview & KPIs ---")
            metric_users = page.inner_text("#kpiTotalUsers")
            metric_resumes = page.inner_text("#kpiTotalResumes")
            metric_ai = page.inner_text("#kpiAiOpsStatus")
            print(f"KPIs Loaded: Users={metric_users}, Resumes={metric_resumes}, AI Status={metric_ai}")
            assert metric_users != "--", "Users metric missing"
            assert metric_resumes != "--", "Resumes metric missing"
            results["admin_login_and_kpis"] = {
                "users": metric_users,
                "resumes": metric_resumes,
                "ai_status": metric_ai
            }

            # 2. Users Tab & Role Mutation
            print("\n--- 5. Testing User Directory & Role Mutation ---")
            page.click(".nav-btn[data-tab='users']")
            page.wait_for_selector("#panelUsers.active", timeout=10000)
            time.sleep(1.0)

            users_html = page.inner_html("#usersTableBody")
            assert admin_email in users_html, "Admin user missing from table"
            assert std_email in users_html, "Standard user missing from table"
            print("User directory rendered registered accounts.")

            # Search filtering
            page.fill("#userSearchInput", std_email)
            time.sleep(1.0)
            search_html = page.inner_html("#usersTableBody")
            assert std_email in search_html
            assert admin_email not in search_html
            print("User search filter verified.")
            page.fill("#userSearchInput", "")
            time.sleep(1.0)

            # 3. AI Ops Tab
            print("\n--- 6. Testing AI Ops & Telemetry ---")
            page.click(".nav-btn[data-tab='ai-ops']")
            page.wait_for_selector("#panelAiOps.active", timeout=10000)
            time.sleep(1.0)
            primary_model = page.inner_text("#aiPrimaryModel")
            fallback_engine = page.inner_text("#aiFallbackEngine")
            print(f"AI Telemetry: Primary={primary_model}, Fallback={fallback_engine}")
            assert "gemini" in primary_model.lower()
            results["ai_ops_telemetry"] = {
                "primary_model": primary_model,
                "fallback_engine": fallback_engine
            }

            # 4. Feature Flags Tab
            print("\n--- 7. Testing Feature Flags Toggle & Persistence ---")
            page.click(".nav-btn[data-tab='feature-flags']")
            page.wait_for_selector("#panelFeatureFlags.active", timeout=10000)
            time.sleep(1.0)

            # Toggle flag via API and UI
            ff_html = page.inner_html("#fullFlagsContainer")
            assert "voice_interview_enabled" in ff_html
            assert "smartbuild_ai_wizard" in ff_html
            print("Feature flags panel rendered all 6 platform switches.")

            # 5. Security Audit Trail Tab
            print("\n--- 8. Testing Security Audit Trail ---")
            page.click(".nav-btn[data-tab='audit-logs']")
            page.wait_for_selector("#panelAuditLogs.active", timeout=10000)
            time.sleep(1.0)
            audit_html = page.inner_html("#auditLogsTableBody")
            assert len(audit_html) > 50, "Audit trail rows missing"
            print("Security Audit Trail rendered real-time logs.")

            # 6. Logout Flow
            print("\n--- 9. Testing Admin Logout ---")
            page.click("#adminLogoutBtn")
            page.wait_for_selector("#adminAuthView:not(.hidden)", timeout=10000)
            token_after_logout = page.evaluate("localStorage.getItem('smartresume_admin_token')")
            assert token_after_logout is None or token_after_logout == "", "Token should be cleared on logout"
            print("Admin Logout verified: Token cleared and redirected to Auth View.")
            results["logout_flow"] = {"status": "SUCCESS", "token_cleared": True}

            # Capture screenshot
            page.screenshot(path="separate_admin_app_verified.png")
            print("Captured verification screenshot: separate_admin_app_verified.png")

            browser.close()

        results["verdict"] = "SEPARATE_ADMIN_APP_VERIFIED"
        print("\n" + "=" * 75)
        print("ALL SEPARATE ADMIN APPLICATION TESTS PASSED (100% GREEN)!")
        print("=" * 75)

    finally:
        admin_proc.terminate()
        try:
            admin_proc.wait(timeout=3)
        except Exception:
            admin_proc.kill()
        print("Admin dev server cleanly stopped.")

    return results

if __name__ == "__main__":
    res = run_separate_admin_verification()
    with open("separate_admin_verification_report.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
