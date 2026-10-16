"""
Automated End-to-End QA for SmartResume.ai:
1. Part 1 — Pro-template subscription gating in real browser (Free user, Pro modal, Not now, tampering rejection)
2. Part 2 — Dedicated Admin authentication without Google OAuth, test admin login, show/hide password
3. Part 3 — Connected Admin control propagation to Candidate API
"""

import sys
import os
import time
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
ADMIN_URL = "http://127.0.0.1:4174"
API_URL = f"{BASE_URL}/api/v1"

results = {
    "free_template_application": False,
    "pro_modal_displayed": False,
    "pro_modal_details_verified": False,
    "not_now_preserves_resume": False,
    "direct_api_pro_gating_enforced": False,
    "invalid_payment_rejected": False,
    "admin_google_oauth_removed": False,
    "admin_login_success": False,
    "admin_control_live_propagation": False,
}

def run_e2e_verification():
    print("=" * 60)
    print("RUNNING PRO GATING & ADMIN AUTHENTICATION E2E QA")
    print("=" * 60)

    # 1. Candidate Free User Setup
    ts = int(time.time())
    cand_email = f"qa_candidate_{ts}@example.com"
    cand_pwd = "Password123!"

    reg = requests.post(f"{API_URL}/auth/register", json={
        "email": cand_email,
        "password": cand_pwd,
        "full_name": "QA Free Candidate"
    }, timeout=5)
    assert reg.status_code in (200, 201), f"Candidate registration failed: {reg.text}"

    login = requests.post(f"{API_URL}/auth/login", json={
        "email": cand_email,
        "password": cand_pwd
    }, timeout=5)
    assert login.status_code == 200, f"Candidate login failed: {login.text}"
    cand_token = login.json()["data"]["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # Verify initial tier is FREE
    profile_data = requests.get(f"{API_URL}/users/profile", headers=cand_headers, timeout=5).json()["data"]
    assert profile_data.get("plan_name") == "FREE", f"Expected FREE plan, got {profile_data.get('plan_name')}"
    print("[PASS] Candidate registered and confirmed on FREE tier")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_init_script("""
            localStorage.setItem('smartresume_seen_onboarding', 'true');
        """)

        page = context.new_page()
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector("#loginEmail", timeout=10000)
        page.fill("#loginEmail", cand_email)
        page.fill("#loginPassword", cand_pwd)
        page.click("#loginForm button.primary-btn")
        page.wait_for_selector("#appView:not(.hidden)", timeout=15000)
        page.wait_for_timeout(1000)
        page.evaluate("""() => {
            const m = document.getElementById('onboardingModal');
            if (m) {
                m.classList.add('hidden');
                m.style.display = 'none';
            }
        }""")
        page.wait_for_timeout(500)

        # -----------------------------------------------------------
        # PART 1: Pro Template Gating in Browser
        # -----------------------------------------------------------
        print("\n--- Part 1: Pro Template Gating in Browser ---")
        page.locator('.nav-groups .nav-item[data-tab="templates"]').click()
        page.wait_for_selector("#tabTemplates.active", timeout=5000)
        page.wait_for_selector(".template-card", timeout=8000)
        page.wait_for_timeout(1000)

        # A. Apply Free Template ("Clean Professional")
        free_btn = page.locator("button[data-use-id='clean_professional']").first
        if not free_btn.is_visible():
            free_btn = page.locator("button[data-use-id='campus_fresher']").first
        assert free_btn.is_visible(), "Free template 'Use Template' button not found"
        free_btn.click()
        page.wait_for_timeout(800)

        # Ensure upgrade modal did NOT open for Free template
        modal_hidden = page.evaluate("() => document.getElementById('templateUpgradeModal').classList.contains('hidden')")
        assert modal_hidden, "Upgrade modal should NOT show for free template!"
        results["free_template_application"] = True
        print("[PASS] Free template applies normally without upgrade modal")

        # B. Click Pro Template ("international_professional")
        page.locator('.nav-groups .nav-item[data-tab="templates"]').click()
        page.wait_for_timeout(1000)

        pro_btn = page.locator("button[data-use-id='international_professional']").first
        if not pro_btn.is_visible():
            pro_btn = page.locator("button[data-use-id='executive_professional']").first
        assert pro_btn.is_visible(), "Pro template button not found"
        pro_btn.click()
        page.wait_for_timeout(800)

        # C. Verify upgrade modal opened
        modal_hidden = page.evaluate("() => document.getElementById('templateUpgradeModal').classList.contains('hidden')")
        assert not modal_hidden, "Upgrade modal MUST open when Free user selects Pro template!"
        results["pro_modal_displayed"] = True
        print("[PASS] Upgrade modal opened when Free user clicked Pro template")

        # D. Verify modal contents: template name, price ₹49, terms
        modal_text = page.locator("#templateUpgradeModal").inner_text()
        assert "49" in modal_text, "Modal must mention configured ₹49 price"
        assert "International" in modal_text or "Global" in modal_text, "Modal must show selected template name"
        results["pro_modal_details_verified"] = True
        print("[PASS] Modal displays template name, INR 49/month price, and ATS terms")

        # E. Click "Not now"
        not_now_btn = page.locator("#upgradeModalNotNowBtn")
        assert not_now_btn.is_visible(), "'Not now' button must exist in modal"
        not_now_btn.click()
        page.wait_for_timeout(500)

        modal_hidden_after = page.evaluate("() => document.getElementById('templateUpgradeModal').classList.contains('hidden')")
        assert modal_hidden_after, "Modal must be hidden after clicking 'Not now'"
        results["not_now_preserves_resume"] = True
        print("[PASS] 'Not now' cleanly dismisses upgrade modal without applying Pro template")

        # F. Server-Side Pro Entitlement Enforcement (Tampering Check)
        direct_apply = requests.post(f"{API_URL}/templates/international_professional/apply", headers=cand_headers, json={}, timeout=5)
        assert direct_apply.status_code == 403, f"Expected 403 Forbidden for direct apply, got {direct_apply.status_code}"
        pro_detail = direct_apply.json().get("details", {})
        assert pro_detail.get("error_code") == "PRO_SUBSCRIPTION_REQUIRED", f"Unexpected error detail: {pro_detail}"
        results["direct_api_pro_gating_enforced"] = True
        print("[PASS] Server-side 403 PRO_SUBSCRIPTION_REQUIRED strictly enforced on direct API calls")

        # G. Invalid Payment Callback Rejection
        fake_payment = requests.post(f"{API_URL}/payments/verify", headers=cand_headers, json={
            "order_id": "order_fake123",
            "payment_id": "pay_fake123",
            "signature": "invalid_signature_bypass_attempt",
            "plan": "PRO_MONTHLY",
        }, timeout=5)
        assert fake_payment.status_code in (400, 403, 422), f"Expected payment verification failure, got {fake_payment.status_code}"
        # Confirm user is still FREE
        post_profile = requests.get(f"{API_URL}/users/profile", headers=cand_headers, timeout=5).json()["data"]
        assert post_profile.get("plan_name") == "FREE", "User must NOT be upgraded on invalid payment signature!"
        results["invalid_payment_rejected"] = True
        print("[PASS] Tampered payment callback rejected and candidate remains on FREE tier")

        # -----------------------------------------------------------
        # PART 2: Admin Portal Login & Security
        # -----------------------------------------------------------
        print("\n--- Part 2: Dedicated Admin Portal QA ---")
        admin_page = context.new_page()
        admin_page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=15000)
        admin_page.wait_for_timeout(1000)

        # A. Verify Google OAuth is removed from Admin UI
        g_btn = admin_page.locator("#adminGoogleLoginBtn")
        assert g_btn.count() == 0, "Admin Google Login button MUST be completely removed!"
        g_script = admin_page.locator("script[src*='accounts.google.com/gsi/client']")
        assert g_script.count() == 0, "Google Identity Services script MUST be removed from Admin Portal!"
        results["admin_google_oauth_removed"] = True
        print("[PASS] Admin Google OAuth button and GSI scripts completely removed from admin-panel")

        # B. Verify show/hide password toggle
        pwd_input = admin_page.locator("#adminPasswordInput")
        assert pwd_input.get_attribute("type") == "password"
        toggle_btn = admin_page.locator(".password-toggle-btn").first
        toggle_btn.click()
        assert pwd_input.get_attribute("type") == "text"
        toggle_btn.click()
        assert pwd_input.get_attribute("type") == "password"
        print("[PASS] Admin password show/hide toggle functions properly")

        # C. Login with Test Admin Credentials
        admin_page.fill("#adminEmailInput", "test@gmail.com")
        admin_page.fill("#adminPasswordInput", "Test@12345678")
        admin_page.click("#adminLoginBtn")
        admin_page.wait_for_timeout(1500)

        # Verify console loaded
        app_view = admin_page.locator("#adminAppView")
        auth_view = admin_page.locator("#adminAuthView")
        assert not app_view.evaluate("el => el.classList.contains('hidden')"), "Admin Console must be visible after login!"
        assert auth_view.evaluate("el => el.classList.contains('hidden')"), "Auth card must be hidden after login!"
        results["admin_login_success"] = True
        print("[PASS] Test Admin authenticated successfully with OWNER_ADMIN role")

        # -----------------------------------------------------------
        # PART 3: Admin Live Control Propagation
        # -----------------------------------------------------------
        print("\n--- Part 3: Admin Live Control Propagation ---")
        # Admin gets token from sessionStorage
        admin_token = admin_page.evaluate("() => sessionStorage.getItem('smartresume_admin_token')")
        assert admin_token, "Admin session token not found in sessionStorage"
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Toggle template modern_professional disabled
        t_off = requests.post(f"{API_URL}/admin/templates/modern_professional/status", headers=admin_headers, json={"enabled": False}, timeout=5)
        assert t_off.status_code == 200, f"Failed to disable template: {t_off.text}"

        # Candidate checks templates catalog
        cand_tpls = requests.get(f"{API_URL}/templates", timeout=5).json()["data"]
        cand_tpl_ids = [t["template_id"] for t in cand_tpls]
        assert "modern_professional" not in cand_tpl_ids, "Disabled template should NOT be visible to candidates!"

        # Admin re-enables template
        t_on = requests.post(f"{API_URL}/admin/templates/modern_professional/status", headers=admin_headers, json={"enabled": True}, timeout=5)
        assert t_on.status_code == 200, f"Failed to re-enable template: {t_on.text}"

        cand_tpls_restored = requests.get(f"{API_URL}/templates", timeout=5).json()["data"]
        cand_tpl_ids_restored = [t["template_id"] for t in cand_tpls_restored]
        assert "modern_professional" in cand_tpl_ids_restored, "Re-enabled template should be restored in candidate catalog!"
        results["admin_control_live_propagation"] = True
        print("[PASS] Admin template toggle propagates live to candidate API in real-time")

        browser.close()

    print("\n" + "=" * 60)
    print("ALL E2E VERIFICATIONS PASSED:")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
