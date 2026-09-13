# SmartResume.ai — Master External Credentials & Environment Checklist

> **Standard:** Complete production specification for all third-party integrations, OAuth providers, payment gateways, and AI models.
> **Security Notice:** Do **NOT** commit real API keys or passwords to version control. Place all active keys in your local \.env\ file.

---

## 1. Credentials Specification Table

| Category | Environment Variable | Provider / Service | Required / Optional | Where to Obtain | Fallback Behavior if Missing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Database** | \DATABASE_URL\ | PostgreSQL 15+ | **Required** | Local PostgreSQL or managed AWS RDS / Supabase / Neon | Application cannot start without persistent storage. |
| **Security** | \JWT_SECRET_KEY\ | Internal / Cryptographic | **Required** | Generate via \openssl rand -hex 32\ (64+ chars recommended) | Refuses startup in production if default/short key is used. |
| **Security** | \JWT_ALGORITHM\ | Internal | Optional (Default: \HS256\) | Standard HMAC SHA-256 | Defaults to \HS256\. |
| **AI (Standard)** | \GEMINI_API_KEY\ | Google AI Studio | Optional | [Google AI Studio](https://aistudio.google.com/) | Uses resilient local rule-based ATS analysis, STAR synthesizer, and STAR interview evaluation. |
| **AI (Models)** | \GEMINI_MODEL_NAME\ | Google AI Studio | Optional (Default: \gemini-3.6-flash\) | Google AI Studio Model List | Defaults to \gemini-3.6-flash\. |
| **AI (Fast/Lite)**| \GEMINI_FAST_MODEL_NAME\ | Google AI Studio | Optional (Default: \gemini-3.5-flash-lite\) | Google AI Studio Model List | Defaults to \gemini-3.5-flash-lite\. |
| **AI (Live)** | \GEMINI_LIVE_MODEL_NAME\ | Google AI Studio | Optional (Default: \gemini-2.0-flash-exp\) | Google AI Studio Live / Multimodal Live API | Informs user with an honest \CONFIGURATION_PENDING\ banner in Live Interview room. |
| **Payments** | \PAYMENTS_MODE\ | Internal Mode Switch | Optional (Default: \mock\) | Set to azorpay\ for live merchant orders | Runs in deterministic mock mode for safe local testing. |
| **Payments** | \PAYMENT_MODE\ | Internal Mode Switch | Optional (Default: \	est\) | Set to \live\ for production banking | Runs in test sandbox mode. |
| **Payments** | \RAZORPAY_KEY_ID\ | Razorpay Merchant Dashboard | Optional in mock, **Required** for live | [Razorpay Dashboard -> Settings -> API Keys](https://dashboard.razorpay.com/#/app/keys) | Falls back to mock order generation if \PAYMENTS_MODE=mock\. |
| **Payments** | \RAZORPAY_KEY_SECRET\ | Razorpay Merchant Dashboard | Optional in mock, **Required** for live | [Razorpay Dashboard -> Settings -> API Keys](https://dashboard.razorpay.com/#/app/keys) | Throws configuration error on signature verification if live mode. |
| **Payments** | \RAZORPAY_WEBHOOK_SECRET\ | Razorpay Merchant Dashboard | Optional in mock, **Required** for live | [Razorpay Dashboard -> Settings -> Webhooks](https://dashboard.razorpay.com/#/app/webhooks) | Webhook signature verification rejected. |
| **Payments** | \RAZORPAY_MONTHLY_PLAN_ID\| Razorpay Subscriptions | Optional | [Razorpay Subscriptions -> Plans](https://dashboard.razorpay.com/#/app/subscriptions) | Subscriptions fallback to standard order billing flow. |
| **Payments** | \RAZORPAY_ANNUAL_PLAN_ID\ | Razorpay Subscriptions | Optional | [Razorpay Subscriptions -> Plans](https://dashboard.razorpay.com/#/app/subscriptions) | Subscriptions fallback to standard order billing flow. |
| **OAuth** | \GOOGLE_CLIENT_ID\ | Google Cloud Console | Optional | [Google Cloud Console -> APIs & Services -> Credentials](https://console.cloud.google.com/apis/credentials) | Shows honest 'Google Sign-In not configured' message; email/pass works. |
| **OAuth** | \GOOGLE_CLIENT_SECRET\ | Google Cloud Console | Optional | [Google Cloud Console -> Credentials](https://console.cloud.google.com/apis/credentials) | OAuth token exchange fails gracefully. |
| **OAuth** | \GOOGLE_REDIRECT_URI\ | Google Cloud Console | Optional (Default: \http://127.0.0.1:3000\) | Must match Authorized Redirect URIs in Google Console | Defaults to base application URL. |
| **OAuth** | \LINKEDIN_CLIENT_ID\ | LinkedIn Developer Portal | Optional | [LinkedIn Developer Portal -> Auth](https://www.linkedin.com/developers/apps) | Shows honest 'LinkedIn Sign-In not configured' message; email/pass works. |
| **OAuth** | \LINKEDIN_CLIENT_SECRET\ | LinkedIn Developer Portal | Optional | [LinkedIn Developer Portal -> Auth](https://www.linkedin.com/developers/apps) | OAuth token exchange fails gracefully. |
| **OAuth** | \LINKEDIN_REDIRECT_URI\ | LinkedIn Developer Portal | Optional (Default: \http://127.0.0.1:3000\) | Must match Authorized Redirect URIs in LinkedIn App | Defaults to base application URL. |
| **Email / SMTP**| \SMTP_HOST\ | SMTP Provider (SendGrid/AWS SES/Gmail) | Optional | Provider Dashboard (e.g. \smtp.sendgrid.net\ or \email-smtp.us-east-1.amazonaws.com\) | In development, tokens logged to console and URL; password reset still verifiable locally. |
| **Email / SMTP**| \SMTP_PORT\ | SMTP Provider | Optional (Default: 87\) | Port 587 (STARTTLS) or 465 (SSL) | Defaults to 587. |
| **Email / SMTP**| \SMTP_USERNAME\ | SMTP Provider | Optional | Provider Account Username | Email sending skipped if absent. |
| **Email / SMTP**| \SMTP_PASSWORD\ | SMTP Provider | Optional | Provider App Password or API Key | Email sending skipped if absent. |
| **Email / SMTP**| \SMTP_FROM_EMAIL\ | SMTP Provider | Optional (Default: oreply@smartresume.ai\) | Verified Sender Address | Defaults to oreply@smartresume.ai\. |
| **Job Feeds** | \JOB_SOURCES_ENABLED\ | Internal Feature Toggle | Optional (Default: \	rue\) | Local configuration | Disables external live job queries; user-added jobs still function. |
| **Job Feeds** | \RAPIDAPI_KEY\ | RapidAPI / JSearch | Optional | [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) | Job Radar falls back to user-saved jobs and honest empty discovery. |
| **Job Feeds** | \ADZUNA_APP_ID\ | Adzuna Developer Portal | Optional | [Adzuna Developer Portal](https://developer.adzuna.com/) | Job Radar falls back to user-saved jobs. |
| **Job Feeds** | \ADZUNA_APP_KEY\ | Adzuna Developer Portal | Optional | [Adzuna Developer Portal](https://developer.adzuna.com/) | Job Radar falls back to user-saved jobs. |

---

## 2. Verification Command

To verify your environment configuration health at any time:
\\ash
pytest backend/tests/test_subscription_lifecycle_and_ux.py backend/tests/test_payments_and_oauth.py
\
