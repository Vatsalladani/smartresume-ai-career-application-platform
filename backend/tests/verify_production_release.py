import json
import requests

PROD_URL = "https://smartresume-ai-career-application-p.vercel.app"

def verify_production():
    print("=" * 70)
    print("CHECKING LIVE VERCEL PRODUCTION DEPLOYMENT")
    print(f"Target: {PROD_URL}")
    print("=" * 70)

    try:
        resp = requests.get(PROD_URL, timeout=15)
        print(f"GET / -> Status {resp.status_code}")
        print("Vercel Headers:")
        for k, v in resp.headers.items():
            if any(term in k.lower() for term in ["vercel", "x-matched-path", "etag", "cache", "age"]):
                print(f"  {k}: {v}")

        html = resp.text
        has_duration = "interviewDurationSelect" in html
        has_dictate = "interviewVoiceDictateBtn" in html
        has_strict = "interviewStrictFocusToggle" in html
        has_focus_coach = "focusCoachPreview" in html
        admin_tab_absent = "tabAdmin" not in html

        print(f"HTML Checks:")
        print(f"  interviewDurationSelect: {has_duration}")
        print(f"  interviewVoiceDictateBtn: {has_dictate}")
        print(f"  interviewStrictFocusToggle: {has_strict}")
        print(f"  focusCoachPreview: {has_focus_coach}")
        print(f"  tabAdmin absent (clean public isolation): {admin_tab_absent}")

        # Check frontend/js/app.js on production
        js_resp = requests.get(f"{PROD_URL}/js/app.js", timeout=15)
        print(f"\nGET /js/app.js -> Status {js_resp.status_code}")
        js_code = js_resp.text
        has_tts = "speakAiText" in js_code
        has_voice_delivery = "voice_delivery_metrics" in js_code
        has_strict_eval = "recordStrictFocusWarning" in js_code
        print(f"  speakAiText in app.js: {has_tts}")
        print(f"  voice_delivery_metrics in app.js: {has_voice_delivery}")
        print(f"  recordStrictFocusWarning in app.js: {has_strict_eval}")

        # Check if backend api is reachable or deployed
        api_health_urls = [
            f"{PROD_URL}/api/v1/health",
            f"{PROD_URL}/health",
            "https://smartresume-ai-backend.onrender.com/api/v1/health",
            "https://smartresume-ai-backend.onrender.com/health"
        ]
        for url in api_health_urls:
            try:
                r = requests.get(url, timeout=5)
                print(f"API probe {url} -> {r.status_code}")
            except Exception as e:
                print(f"API probe {url} -> failed: {e}")

    except Exception as e:
        print(f"Error checking production: {e}")

if __name__ == "__main__":
    verify_production()
