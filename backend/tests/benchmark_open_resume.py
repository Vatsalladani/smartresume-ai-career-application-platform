import sys
import os
import time
import socket
import subprocess
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.user import User
from app.models.resume import Resume
from app.core.security import hash_password
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def run_benchmark(label="BEFORE OPTIMIZATION"):
    print("=" * 70)
    print(f"BENCHMARK: PROFILE -> OPEN RESUME LATENCY ({label})")
    print("=" * 70)

    backend_proc = None
    if not is_port_in_use(8000):
        print("Starting FastAPI backend server on 8000...")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(backend_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            if is_port_in_use(8000):
                break
            time.sleep(0.5)
        time.sleep(1.0)

    db = SessionLocal()
    ts = int(time.time() * 1000)
    user_email = f"benchmark_user_{ts}@smartresume.ai"
    user_pw = "BenchmarkPass123!"

    user = User(
        email=user_email,
        password_hash=hash_password(user_pw),
        full_name="Benchmark Candidate",
        is_active=True,
        is_verified=True,
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Add a comprehensive test resume
    resume_content = {
        "header": {
            "name": "Benchmark Candidate",
            "headline": "Staff Distributed Systems Engineer",
            "email": user_email,
            "phone": "+1 (555) 019-2834",
            "location": "San Francisco, CA",
            "links": [{"label": "GitHub", "url": "https://github.com/benchmark"}]
        },
        "summary": "Accomplished Distributed Systems Engineer with 10+ years designing high-throughput microservices and fault-tolerant architectures.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Distributed Consensus", "gRPC"],
        "experiences": [
            {
                "title": "Principal Architect",
                "company": "CloudScale Global",
                "location": "San Francisco, CA",
                "startDate": "2021-01",
                "endDate": "Present",
                "current": True,
                "bullets": [
                    "Engineered distributed event-driven pipeline processing 45k RPS with 99.99% availability.",
                    "Reduced p99 API latency from 240ms to 42ms via caching tiers and query optimization."
                ]
            },
            {
                "title": "Senior Backend Engineer",
                "company": "DataMesh Systems",
                "location": "Palo Alto, CA",
                "startDate": "2017-03",
                "endDate": "2020-12",
                "current": False,
                "bullets": [
                    "Designed mission-critical billing infrastructure handling $20M+ monthly transactions.",
                    "Led engineering team of 8 engineers across 4 international time zones."
                ]
            }
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "University of California, Berkeley",
                "year": "2016"
            }
        ],
        "template": "classic_ats"
    }

    test_resume = Resume(
        user_id=user.id,
        title="Staff Engineer Master Resume",
        target_role="Staff Distributed Systems Engineer",
        target_company="Stripe",
        parsed_content=resume_content,
        ats_score=95,
        is_archived=False,
    )
    db.add(test_resume)

    # Add second distinct resume
    resume2_content = {
        "header": {
            "name": "Benchmark Candidate",
            "headline": "Lead Frontend Architect",
            "email": user_email,
            "phone": "+1 (555) 019-2834",
            "location": "New York, NY",
        },
        "summary": "Specialist in high-performance web applications, Design Systems, and micro-frontends.",
        "skills": ["TypeScript", "React", "Next.js", "GraphQL", "Tailwind CSS", "Web Workers"],
        "experiences": [
            {
                "title": "Lead UI Architect",
                "company": "Veloce Technologies",
                "location": "New York, NY",
                "startDate": "2022-04",
                "endDate": "Present",
                "current": True,
                "bullets": ["Architected design system adopted by 120+ engineers."]
            }
        ]
    }
    test_resume2 = Resume(
        user_id=user.id,
        title="Frontend Architect Master Resume",
        target_role="Lead Frontend Architect",
        target_company="Vercel",
        parsed_content=resume2_content,
        ats_score=85,
        is_archived=False,
    )
    db.add(test_resume2)
    db.commit()
    db.refresh(test_resume)
    db.refresh(test_resume2)
    print(f"Created candidate with Resume 1 (#{test_resume.id}) and Resume 2 (#{test_resume2.id})")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_init_script("localStorage.setItem('smartresume_seen_onboarding', 'true');")
            page = context.new_page()

            network_requests = []
            page.on("request", lambda r: network_requests.append(r.url))

            # 1. Login
            page.goto(f"{BASE_URL}/#login", wait_until="networkidle")
            page.fill("#loginEmail", user_email)
            page.fill("#loginPassword", user_pw)
            page.click("button[type='submit']")

            page.wait_for_selector("#tabDashboard.active", timeout=10000)
            print("Successfully authenticated and landed on Dashboard.")

            # Ensure onboarding modal is closed
            page.evaluate("() => { localStorage.setItem('smartresume_seen_onboarding', 'true'); const m = document.getElementById('onboardingModal'); if (m) { m.classList.add('hidden'); m.style.display = 'none'; } }")
            time.sleep(0.5)

            # 2. Navigate to Profile
            page.click("button[data-tab='profile']")
            page.wait_for_selector("#tabProfile.active", timeout=10000)
            time.sleep(1.0)
            print("Landed on Profile tab.")

            open_btn = page.query_selector("#profileOpenBestResumeBtn")
            assert open_btn is not None, "profileOpenBestResumeBtn not found!"

            network_requests.clear()

            # 3. Benchmark click -> navigation & render
            t_start = time.perf_counter()
            open_btn.click()

            page.wait_for_selector("#tabResumeBuilder.active", timeout=10000)
            t_nav = time.perf_counter()
            nav_latency_ms = (t_nav - t_start) * 1000

            page.wait_for_function(
                "() => { const t = document.getElementById('builderResumeTitle')?.textContent || ''; const chip = document.getElementById('builderResumeTargetChip')?.textContent || ''; const c = document.getElementById('builderPreviewCanvas')?.innerText || ''; return t.includes('Staff Engineer Master Resume') || chip.includes('Staff Distributed Systems Engineer') || c.includes('Benchmark Candidate'); }",
                timeout=15000
            )
            t_render = time.perf_counter()
            render_latency_ms = (t_render - t_start) * 1000

            relevant_calls = [u for u in network_requests if "/api/v1/" in u or "/profile/health" in u]
            health_calls = [u for u in relevant_calls if "profile/health" in u]
            resume_calls = [u for u in relevant_calls if "/resumes" in u]

            print(f"\n--- PERFORMANCE RESULTS ({label}) ---")
            print(f"Click-to-Navigation Time:   {nav_latency_ms:.1f} ms")
            print(f"Click-to-Content Render:    {render_latency_ms:.1f} ms")
            print(f"Total API Requests Made:    {len(relevant_calls)}")
            print(f"  /profile/health requests: {len(health_calls)}")
            print(f"  /resumes/* requests:      {len(resume_calls)}")
            for idx, call in enumerate(relevant_calls):
                print(f"    [{idx+1}] {call}")

            # 4. Verify Content Integrity for Resume 1
            canvas_text1 = page.evaluate("() => document.getElementById('builderPreviewCanvas')?.innerText || ''")
            assert "Staff Distributed Systems Engineer" in canvas_text1 or "CloudScale Global" in canvas_text1, "Resume 1 content missing from canvas!"
            assert "Veloce Technologies" not in canvas_text1, "Cross-contamination: Resume 2 content leaked into Resume 1!"
            print("Verified Resume 1 content integrity & zero leakage.")

            # 5. Switch to Resume 2 and verify zero data contamination
            print("\nSwitching to Resume 2 (#" + str(test_resume2.id) + ")...")
            page.evaluate(f"() => openResume({test_resume2.id})")
            time.sleep(0.5)
            page.wait_for_function(
                "() => { const c = document.getElementById('builderPreviewCanvas')?.innerText || ''; return c.includes('Veloce Technologies') || c.includes('Lead UI Architect'); }",
                timeout=10000
            )
            canvas_text2 = page.evaluate("() => document.getElementById('builderPreviewCanvas')?.innerText || ''")
            assert "Lead UI Architect" in canvas_text2 or "Veloce Technologies" in canvas_text2, "Resume 2 content missing from canvas!"
            assert "CloudScale Global" not in canvas_text2, "Cross-contamination: Resume 1 content leaked into Resume 2!"
            print("Verified Resume 2 content integrity & zero leakage.")

            # 6. Switch back to Resume 1
            print("Switching back to Resume 1...")
            page.evaluate(f"() => openResume({test_resume.id})")
            time.sleep(0.5)
            page.wait_for_function(
                "() => { const c = document.getElementById('builderPreviewCanvas')?.innerText || ''; return c.includes('CloudScale Global'); }",
                timeout=10000
            )
            print("Verified clean return to Resume 1.")

            # 7. Reload page and confirm persistence
            print("Reloading page to test refresh persistence...")
            page.reload(wait_until="networkidle")
            page.wait_for_selector("#tabDashboard.active, #tabResumeBuilder.active", timeout=10000)
            page.evaluate(f"() => navigateToTab('resume-builder')")
            time.sleep(0.5)
            canvas_reloaded = page.evaluate("() => document.getElementById('builderPreviewCanvas')?.innerText || ''")
            assert "CloudScale Global" in canvas_reloaded, "Reload failed to maintain active resume content!"
            print("Verified refresh persistence.")

            browser.close()

            print("\n======================================================================")
            print("OPEN RESUME PERFORMANCE & REGRESSION CHECKS: 100% PASSED!")
            print("======================================================================")

            return {
                "nav_latency_ms": nav_latency_ms,
                "render_latency_ms": render_latency_ms,
                "total_requests": len(relevant_calls),
            }

    finally:
        db.close()
        if backend_proc:
            backend_proc.terminate()

if __name__ == "__main__":
    run_benchmark("AFTER OPTIMIZATION")
