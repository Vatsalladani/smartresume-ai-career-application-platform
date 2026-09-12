# SmartResume.ai — Evidence-Grounded ATS SaaS Platform

[![Tests](https://img.shields.io/badge/tests-41%20passed-brightgreen.svg)](backend/tests)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](backend/)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-teal.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

SmartResume.ai is an enterprise-grade, evidence-grounded ATS resume platform and job-search copilot built with FastAPI, PostgreSQL, SQLAlchemy, ReportLab, python-docx, and vanilla JavaScript.

Unlike conventional generative AI tools that hallucinate candidate accomplishments, SmartResume.ai operates on an **Evidence-Grounded Architecture**: resumes are tailored strictly from verified facts inside a candidate's Master Profile, eliminating fabricated metrics, fake titles, and synthetic claims.

---

## Table of Contents
- [Architecture & Core Principles](#architecture--core-principles)
- [Key Features](#key-features)
- [Security Audit & Compliance (All 15 Defects Resolved)](#security-audit--compliance)
- [Social Authentication (OAuth 2.0)](#social-authentication-oauth-20)
- [Database & Migrations](#database--migrations)
- [API Reference](#api-reference)
- [Local Setup & Running](#local-setup--running)
- [Automated Testing (41/41 Tests Passing)](#automated-testing)
- [Subscription & Billing Architecture](#subscription--billing-architecture)
- [Production Deployment Checklist](#production-deployment-checklist)

---

## Architecture & Core Principles

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    Single-Page App (SPA)                    │
  │   Dashboard | Master Profile | Job Fit | Tailor | Tracker   │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ REST API / JWT
  ┌──────────────────────────────▼──────────────────────────────┐
  │                   FastAPI Backend Service                   │
  │  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────┐  │
  │  │ Security Headers│ │ Granular Limits  │ │ JWT Rotation │  │
  │  └─────────────────┘ └──────────────────┘ └──────────────┘  │
  │                                                             │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │ Core Engines:                                         │  │
  │  │ • Master Profile & AI Parsing + Mandatory Human Review │  │
  │  │ • Job Requirement Extractor (Must-Have vs Preferred)  │  │
  │  │ • Evidence Map Engine (Strong, Partial, Missing)      │  │
  │  │ • Explainable ATS Scorer (4-part deterministic score)  │  │
  │  │ • Anti-Fabrication Tailoring & Side-by-Side Diff      │  │
  │  │ • 4 ATS-Safe Templates (ReportLab PDF & python-docx)  │  │
  │  │ • Billing & Quota Manager (RBI e-mandate compliant)   │  │
  │  │ • Multi-Currency Engine (INR, USD, EUR, GBP, etc.)    │  │
  │  │ • Google & LinkedIn OAuth 2.0 Integration             │  │
  │  └───────────────────────────────────────────────────────┘  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │                PostgreSQL Relational Storage                │
  │ Master Profiles • Job Postings • Requirements • Versions    │
  │ ATS Checks • Evidence Links • Usage Counters • Payment Evts │
  └─────────────────────────────────────────────────────────────┘
```

1. **Master Profile as Single Source of Truth**: Candidate skills, accomplishments, projects, and employment history reside in verified records.
2. **Zero-Fabrication Guarantee**: Missing evidence triggers actionable honesty hints rather than hallucinated resume bullets.
3. **Mandatory Human Review**: Uploaded resumes (PDF/DOCX/TXT) are parsed into an editable draft and require candidate verification before committing.
4. **Deterministic ATS Scoring**: Score is composed of 4 explainable pillars (Evidence Match 40%, Keyword Coverage 30%, Format Health 15%, Content Quality 15%).
5. **Immutable Version Snapshots**: Each tailored application snapshot is permanently archived with its diff summary, template, and score.
6. **Round-Trip Verified ATS Templates**: 4 templates (`classic_ats`, `technical_ats`, `campus_fresher`, `professional`) verified for character-level round-trip text extraction in PDF and DOCX.

---

## Key Features

### 0. Unified Dashboard
- Visual overview with profile evidence grounding meter.
- Real-time monthly usage counters and progress bars (Fits, Tailors, Exports).
- Quick action shortcuts (New Job Match, Edit Profile, Track Application, View Plans).
- High-level list of recent job applications and target job postings.

### 1. Master Profile Editor
- Comprehensive candidate representation: Headline, summary, contact info, work experiences with bullets, key projects, education history, categorized skills, and verified certifications.
- Real-time profile completeness meter (0–100%) highlighting missing sections.
- AI resume importer supporting PDF, DOCX, and raw text with structured draft extraction and human-in-the-loop review modal.
- Rich, intuitive empty states across all sub-entities with direct call-to-action triggers.

### 2. Job Description & Fit Engine
- Ingests raw job descriptions and automatically classifies requirements into `MUST_HAVE` and `PREFERRED`.
- Evaluates candidate profile evidence against every requirement to produce an interactive **Evidence Map** with `STRONG`, `PARTIAL`, `MISSING`, or `UNCLEAR` ratings.
- Actionable ATS guidance explaining how to strengthen weak points without fabricating experience.

### 3. AI Tailoring Studio
- Generates tailored bullet proposals targeting specific requirements.
- Side-by-side diff review allowing individual **Accept** or **Reject** toggles for every single bullet, plus **Accept All** and **Reject All** actions.
- **Honest Gaps Banner**: Explicitly lists skills that were left out due to absence of verified evidence, coaching the candidate on what real-world projects or certifications to pursue.
- Saves immutable version snapshots with user-defined changelog and selected ATS template.

### 4. 4 ATS-Safe Templates (PDF & DOCX)
- **Classic ATS**: Single-column standard corporate format, universally compatible with Taleo, Workday, Greenhouse, and Lever.
- **Technical ATS**: Prominently highlights verified technical stacks, programming languages, and architecture achievements.
- **Campus / Fresher**: Prioritizes academic credentials, coursework, capstone projects, and internships.
- **Professional**: Emphasizes leadership, executive summaries, and business metric impact.
- Generates standard PDF documents via ReportLab and DOCX documents via python-docx.

### 5. Application Tracker
- Tracks candidate applications through the hiring lifecycle: `SAVED` → `APPLIED` → `INTERVIEW` → `OFFER` → `REJECTED`.
- Links tracked applications directly to the exact immutable `ApplicationVersion` snapshot and target job description.

### 6. Billing, Quotas & Multi-Currency Engine
- Multi-Currency selector: Real-time pricing across **INR (₹)**, **USD ($)**, **EUR (€)**, **GBP (£)**, **AED (AED)**, **CAD (CA$)**, **AUD (A$)**, **SGD (S$)**, and **JPY (¥)**.
- **₹1 Sandbox / Single Export Test**:
  - One-time test verification purchase granting 1 export credit without creating recurring charges.
  - Serves dynamic Test UPI ID: `ladanivatsal8892@oksbi`.
  - Supports instant simulated capture in test mode and live Razorpay checkout.
- Recurring Subscriptions:
  - **Free Plan**: ₹0/mo (2 fits, 2 tailored versions, 2 exports).
  - **Pro Monthly**: ₹79/mo (50 fits, 30 tailored versions, 20 exports).
  - **Annual Power**: ₹699/yr (1,000 fits, 500 tailored versions, 500 exports).
  - **Booster Packs**: ₹29 Quick Apply, ₹49 Weekend Sprint, ₹99 Interview Blast.
- **RBI e-Mandate Regulatory Compliance**:
  - Pre-checkout Recurring Consent Modal disclosing debit frequency, maximum debit amount, and cancellation terms.
  - 1-click instant subscription cancellation from Billing tab.
- Webhook idempotency table (`payment_events`) preventing duplicate credits.
- Dynamic Payment History table tracking all transactions.

---

## Social Authentication (OAuth 2.0)

SmartResume.ai includes backend endpoints for Google and LinkedIn OAuth 2.0 authentication:
- `/api/v1/auth/oauth/config` — Checks if OAuth credentials are configured.
- `/api/v1/auth/oauth/google/url` & `/api/v1/auth/oauth/linkedin/url` — Generates authorization URLs.
- `/api/v1/auth/oauth/google/callback` & `/api/v1/auth/oauth/linkedin/callback` — Validates authorization codes, syncs profiles, and creates authenticated sessions.
- In development/sandbox mode when credentials are not yet set, the UI presents a helpful setup guide rather than crashing or faking sign-in.

---

## Security Audit & Compliance

All 15 baseline security defects identified in the Definitive Master Implementation Prompt have been fully closed and verified by automated tests:

| Defect ID | Description | Solution Implemented |
|---|---|---|
| **SEC-01** | Production secret default fallback | `validate_production_secrets()` aborts server start in production if defaults are detected |
| **SEC-02** | Password reset token leak in API response | Token removed from response body; only confirmation message returned |
| **SEC-03** | User enumeration in forgot password | Constant generic response returned regardless of email existence |
| **SEC-04** | Email verification token leak | Token omitted from API registration responses |
| **SEC-05** | Deactivated users login ability | `is_active` checked on login and token verification |
| **SEC-06** | Razorpay webhook duplicate credit | Idempotency enforced via `PaymentEvent` table logging provider & event ID |
| **SEC-07** | Loose CORS configuration | Replaced wildcard with explicit origin allowlist (`3000`, `5500`) |
| **SEC-08** | Deprecated AI model | Upgraded to `gemini-3.6-flash` default with `gemini-3.5-flash-lite` cost-saving tier |
| **SEC-09** | Unthrottled endpoints | Granular IP rate limiting: Auth 10/min, AI/Jobs 15/min, General 120/min |
| **SEC-10** | Hardcoded pricing | Centralized in `core/config.py` with multi-tier INR and booster pack support |
| **SEC-11** | Request size vulnerability | Enforced `RequestSizeLimitMiddleware` (12MB max request body) |
| **SEC-12** | Upload file size vulnerability | Enforced 10MB limit on resume uploads |
| **SEC-13** | Token revocation gap | Blacklist verification on every authenticated request via JTI hash |
| **SEC-14** | Account lockout bypass | 5 failed attempts locks account for 15 minutes |
| **SEC-15** | Prompt injection vulnerability | Strict delimiters and sanitized input validation on AI prompts |

---

## Database & Migrations

The database layer is managed through Alembic and PostgreSQL.

### Migration History
- `0001_initial`: Users, Subscriptions, Resumes, ResumeVersions, ATSAnalyses, JobApplications, RefreshTokens, AuditLogs, RevokedTokens.
- `0002_master_profile_and_evidence`: Profiles, Experiences, Projects, Education, Skills, Certifications, JobPostings, JobRequirements, EvidenceLinks, ApplicationVersions, ATSChecks, PaymentEvents, UsageCounters.
- `0003_application_links`: Adds `job_posting_id` and `version_id` foreign keys to `job_applications`.

To apply migrations:
```bash
cd backend
alembic upgrade head
```

---

## API Reference

### Master Profile
- `GET /api/v1/profile` — Fetch current user's Master Profile and completeness score
- `PUT /api/v1/profile` — Update headline, summary, and contact information
- `POST /api/v1/profile/experiences` — Add work experience
- `PUT /api/v1/profile/experiences/{id}` — Update work experience
- `DELETE /api/v1/profile/experiences/{id}` — Delete work experience
- `POST /api/v1/profile/projects` — Add project
- `PUT /api/v1/profile/projects/{id}` — Update project
- `DELETE /api/v1/profile/projects/{id}` — Delete project
- `POST /api/v1/profile/education` — Add education record
- `DELETE /api/v1/profile/education/{id}` — Delete education record
- `POST /api/v1/profile/skills` — Add verified skill
- `DELETE /api/v1/profile/skills/{id}` — Delete verified skill
- `POST /api/v1/profile/certifications` — Add certification
- `DELETE /api/v1/profile/certifications/{id}` — Delete certification
- `POST /api/v1/profile/import` — Parse uploaded resume file/text into a review draft
- `POST /api/v1/profile/import/commit` — Commit reviewed draft to Master Profile

### Job Match & Fit Engine
- `POST /api/v1/jobs` — Create target job posting and extract requirements
- `GET /api/v1/jobs` — List user's target job postings
- `GET /api/v1/jobs/{id}` — Get single job posting details
- `DELETE /api/v1/jobs/{id}` — Delete target job posting
- `POST /api/v1/jobs/{id}/fit-analysis` — Run deterministic ATS fit analysis & Evidence Map

### Tailoring Studio & Exports
- `POST /api/v1/jobs/{id}/tailor` — Generate evidence-grounded tailoring proposal and diff
- `POST /api/v1/jobs/{id}/versions` — Commit immutable application version snapshot
- `GET /api/v1/jobs/{id}/versions` — List version snapshots for a job
- `GET /api/v1/jobs/{id}/versions/{version_id}` — Get single version snapshot
- `GET /api/v1/jobs/{id}/versions/{version_id}/export?format=pdf|docx&template=...` — Download formatted ATS-safe resume

### Applications Tracker
- `POST /api/v1/applications` — Save tracked job application
- `GET /api/v1/applications` — List tracked applications
- `PATCH /api/v1/applications/{id}` — Update status (`SAVED`, `APPLIED`, `INTERVIEW`, `OFFER`, `REJECTED`)
- `DELETE /api/v1/applications/{id}` — Delete application

### Billing & Payments
- `GET /api/v1/payments/billing-summary` — Current plan, quota usage, and reset date
- `POST /api/v1/payments/create-order` — Create Razorpay order
- `POST /api/v1/payments/webhooks/razorpay` — Webhook handler with idempotency
- `POST /api/v1/payments/cancel` — 1-click subscription cancellation

---

## Local Setup & Running

### Prerequisites
- Python 3.12+
- PostgreSQL (or local SQLite for dev/testing)
- Node.js / HTTP server for frontend

### 1. Clone & Configure Environment
```bash
cp .env.example .env
```
Ensure `.env` contains your database URL and settings.

### 2. Start Backend Service
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Start Frontend Dashboard
In a separate terminal:
```bash
cd frontend
python -m http.server 3000
```
Open [http://127.0.0.1:3000](http://127.0.0.1:3000) in your browser.

---

## Automated Testing

SmartResume.ai comes with a complete, automated test suite covering all security controls, profile CRUD, fit engine scoring, AI tailoring diffs, ReportLab/python-docx round-trip exports, billing quotas, and application tracking.

To run the full test suite:
```powershell
# In PowerShell:
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```

```bash
# In Bash:
PYTHONPATH=backend pytest backend/tests -v
```

### Test Suite Structure:
- `backend/tests/test_security_phase1.py` — Verifies token leaks, enumeration protection, rate limiting, and webhook idempotency.
- `backend/tests/test_master_profile.py` — Profile CRUD, completeness calculation, resume parsing, and mandatory review commit.
- `backend/tests/test_fit_engine.py` — Requirement extraction, Evidence Map matching, and 4-factor ATS scoring.
- `backend/tests/test_tailoring_versions.py` — Side-by-side bullet diff generation, accept/reject mechanics, and immutable version snapshots.
- `backend/tests/test_resume_export.py` — ReportLab PDF generation, python-docx generation across all 4 templates, and `pypdf.PdfReader` round-trip text extraction verification.
- `backend/tests/test_billing_quotas.py` — Free tier quota limits, Pro tier upgrades, and billing summary endpoints.
- backend/tests/test_applications.py — Application tracker with linked version snapshots and status transitions.
- backend/tests/test_payments_and_oauth.py — Multi-currency pricing, ₹1 test payment flow, RBI mandate disclosure, and OAuth configuration checks.
- backend/tests/test_ai_service.py & test_password_validator.py — AI schema validation and password entropy verification.

---

## Subscription & Billing Architecture

```
                 ┌────────────────────────────────┐
                 │  User Requests Fit / Tailor /  │
                 │             Export             │
                 └───────────────┬────────────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │ Usage Counter Check (Month) │
                  └──────────────┬──────────────┘
                    /                       \
        [Within Quota]                     [Quota Exceeded]
              │                                    │
       Proceed with Request               HTTP 402 / 429
       Increment Counter              Upgrade Prompt (₹79/mo)
                                                   │
                                      ┌────────────▼────────────┐
                                      │   Razorpay Checkout     │
                                      └────────────┬────────────┘
                                                   │ Webhook
                                      ┌────────────▼────────────┐
                                      │ PaymentEvent (Idempotent│
                                      │ Log event_id in DB)     │
                                      └────────────┬────────────┘
                                                   │
                                      ┌────────────▼────────────┐
                                      │ Activate PRO / Upgrade  │
                                      └─────────────────────────┘
```

---

## Production Deployment Checklist

1. **Environment Security**:
   - Set `ENVIRONMENT=production`
   - Generate a cryptographically secure `JWT_SECRET_KEY` (minimum 64 characters)
   - Restrict `ALLOWED_ORIGINS` strictly to production domain(s)
2. **Database Management**:
   - Point `DATABASE_URL` to a high-availability PostgreSQL instance
   - Execute `alembic upgrade head` during deployment
   - Enable automated backups and point-in-time recovery
3. **Payments Integration**:
   - Set `PAYMENTS_MODE=razorpay`
   - Store `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` in secret manager
   - Configure webhook endpoint in Razorpay dashboard: `https://api.yourdomain.com/api/v1/payments/webhooks/razorpay`
4. **AI Gateway**:
   - Set `GEMINI_API_KEY` with production quota limits
   - Configure Gemini 3.6 Flash for general analysis and Gemini 3.5 Flash-Lite for high-throughput tasks
5. **Reverse Proxy & TLS**:
   - Configure NGINX or Cloudflare with TLS 1.3
   - Match client request body limits (`client_max_body_size 12M`)
   - Forward real client IP headers (`X-Forwarded-For`) for accurate rate limiting
