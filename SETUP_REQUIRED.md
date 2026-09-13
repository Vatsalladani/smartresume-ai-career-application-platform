# SmartResume.ai — Master Setup & Architecture Guide

Welcome to **SmartResume.ai** — the comprehensive AI Career & Job Application Operating System.
This document outlines everything required to configure, initialize, run, and maintain the platform.

---

## 1. System Architecture Overview

SmartResume.ai is engineered as a unified, evidence-grounded Career OS:
- **Backend**: FastAPI (Python 3.11+) + SQLAlchemy ORM + Pydantic v2
- **Database**: PostgreSQL 14+ with Alembic version-controlled migrations
- **Frontend**: Responsive HTML5 + Vanilla JS (ES6+) + CSS3 design system
- **AI Engine**: Google Gemini (Direct API / Vertex AI) with anti-hallucination & anti-fabrication guardrails
- **Payment & Subscriptions**: Razorpay Payment Gateway (UPI, Cards, NetBanking, 7-Day Pro Trial ₹0, ₹1 first export, ₹49/mo, ₹399/yr)
- **Browser Extension**: Manifest V3 SmartApply Copilot for assisted application filling without unauthorized scraping or bots

```
   ┌────────────────────────────────────────────────────────────┐
   │                     SmartResume.ai                         │
   │               Evidence-Grounded Career OS                  │
   └─────────────────────────────┬──────────────────────────────┘
                                 │
         ┌───────────────────────┼────────────────────────┐
         │                       │                        │
         ▼                       ▼                        ▼
 ┌───────────────┐       ┌───────────────┐       ┌─────────────────┐
 │ Master Profile│       │Evidence Vault │       │  SmartBuild AI  │
 │  & Past Data  │◄─────►│ (Ground Truth)│◄─────►│  STAR Synthesis │
 └───────┬───────┘       └───────┬───────┘       └────────┬────────┘
         │                       │                        │
         ▼                       ▼                        ▼
 ┌───────────────┐       ┌───────────────┐       ┌─────────────────┐
 │   Job Radar   │       │  Job Parsing  │       │Application Pack │
 │ Match/Stretch │◄─────►│& Fit Analysis │◄─────►│ 13 Career Assets│
 └───────────────┘       └───────┬───────┘       └────────┬────────┘
                                 │                        │
                                 ▼                        ▼
                         ┌───────────────┐       ┌─────────────────┐
                         │ Mock Interview│       │SmartApply Copilot│
                         │Copilot (Voice)│       │ (Chrome Ext V3) │
                         └───────────────┘       └─────────────────┘
```

---

## 2. Quickstart Instructions

### 2.1 Clone & Environment Setup
```bash
cd "E:\RESUME SaaS ANTIGRAVITY"
```

### 2.2 Python Virtual Environment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install all requirements
pip install -r requirements.txt
```

### 2.3 Environment Variables (.env)
Create or edit `backend/.env` with the following keys:

```env
# Server & Environment
ENVIRONMENT=development
PORT=8000
FRONTEND_URL=http://localhost:8000

# Security & Tokens
SECRET_KEY=your_super_secret_64_character_hex_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=10080
ALGORITHM=HS256

# PostgreSQL Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/resume_saas_db

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# Razorpay Payments
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
UPI_VPA=ladanivatsal8892@oksbi

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# LinkedIn OAuth 2.0
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/auth/linkedin/callback
```

### 2.4 Apply Database Migrations
```bash
cd backend
alembic upgrade head
```

### 2.5 Run Backend & Frontend Server
The FastAPI backend serves the frontend static directory directly at `/`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at:
`http://localhost:8000`

---

## 3. Dedicated Setup Guides

For detailed setup of each external subsystem, consult the dedicated guides:
- **Database (PostgreSQL & Alembic)**: [`DATABASE_SETUP.md`](./DATABASE_SETUP.md)
- **AI Grounding & Gemini Engine**: [`GEMINI_SETUP.md`](./GEMINI_SETUP.md)
- **Payments & Webhooks (Razorpay & UPI)**: [`RAZORPAY_SETUP.md`](./RAZORPAY_SETUP.md)
- **Google OAuth Login**: [`GOOGLE_OAUTH_SETUP.md`](./GOOGLE_OAUTH_SETUP.md)
- **LinkedIn OAuth Login**: [`LINKEDIN_OAUTH_SETUP.md`](./LINKEDIN_OAUTH_SETUP.md)
- **SmartApply Chrome Extension (Manifest V3)**: [`SMARTAPPLY_SETUP.md`](./SMARTAPPLY_SETUP.md)

---

## 4. Verification & Testing

To run the complete automated test suite covering all 98 integration, unit, and lifecycle tests:
```bash
cd backend
pytest -v
```

All 98 tests pass across:
1. AI Service & Guardrails (`test_ai_service.py`)
2. Application Tracking (`test_applications.py`)
3. Billing Quotas & Monthly Reset (`test_billing_quotas.py`)
4. Subscription Lifecycle & UX Matrix (`test_subscription_lifecycle_and_ux.py` — 20 test cases)
5. Career OS & Application OS (`test_career_and_application_os.py`)
6. Company Verification & Trust Scores (`test_company_verification.py`)
7. Fit Engine & Role Grounding (`test_fit_engine.py`)
8. Full Journey End-to-End (`test_full_journey_e2e.py`)
9. Product Intelligence v2 Rules (`test_intelligence_v2.py`)
10. AI Interview Copilot (`test_interview_copilot.py`)
11. Master Profile CRUD & Verification (`test_master_profile.py`)
12. Password Validator & Security Policies (`test_password_validator.py`)
13. Payment Verification & Webhook Handling (`test_payments_and_oauth.py`)
14. Resume Export (PDF & DOCX) (`test_resume_export.py`)
15. Security & Authentication Phase 1 (`test_security_phase1.py`)
16. Tailoring & Immutable Versions (`test_tailoring_versions.py`)
17. Templates & Guidance System (`test_templates_and_guidance.py`)

---

## 5. Security, Billing & Operational Checklist

- [x] Passwords hashed with Bcrypt (cost factor 12)
- [x] JWT tokens with configurable TTL and HS256 algorithm
- [x] Anti-fabrication check on all AI generation endpoints
- [x] Strictly no fake ATS scores or vanity metrics
- [x] Single-claim 7-Day Pro Trial without automatic credit card charging
- [x] Strict isolation between ₹1 one-time export purchases and ₹1 recurring mandate authorizations
- [x] Payment-method-aware subscription management: UPI AutoPay mandate instructions inside UPI apps vs Card recurring in-app cancellation
- [x] Access preserved until paid billing cycle end (`ENDING` status) upon cancellation
- [x] 6-Pillar Billing layout: Your Plan, Usage & Quotas, Plans, One-Time Options, Manage Subscription, Payment History
- [x] Zero developer/test terminology exposed in customer views
- [x] Extension requests verified via Bearer JWT with zero DOM scraping or automated submitting
- [x] Database transactions protected with foreign key cascades, migration tracking (Alembic), and integrity constraints
