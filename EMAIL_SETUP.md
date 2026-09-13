# SmartResume.ai — Email & SMTP Configuration Guide

This document specifies the setup procedure for the production transactional email system for **SmartResume.ai**.

---

## 1. Architecture & Overview

SmartResume.ai utilizes transactional email for:
1. **User Email Verification**: Sent immediately upon signup with an encrypted 24-hour verification token.
2. **Password Resets**: Sent on forgot-password requests with a secure 20-minute expiring token.
3. **Application & Interview Reminders**: System notifications sent when critical milestones or follow-ups occur.

### Graceful Fallback Policy
- **Zero Simulation Rule**: If SMTP credentials are not configured in the active environment, the application logs a `[EMAIL_SERVICE: CONFIGURATION_PENDING]` notice to the server logs and returns an honest informational notice.
- No false "email delivered" toasts are displayed to the user.

---

## 2. Environment Variables

Configure the following variables in your `backend/.env` or root `.env`:

| Variable | Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `SMTP_HOST` | string | `smtp.sendgrid.net` | The hostname of your SMTP relay server. |
| `SMTP_PORT` | integer | `587` | Port `587` (STARTTLS) or `465` (SSL/TLS). Default: `587`. |
| `SMTP_USERNAME`| string | `apikey` | The authentication username for your provider. |
| `SMTP_PASSWORD`| string | `SG.xxxxxxxxxx` | App password or API key. |
| `SMTP_FROM_EMAIL`| string | `noreply@smartresume.ai` | Verified domain sender address. |
| `SMTP_TLS` | boolean | `true` | Set `true` to enforce STARTTLS encryption on port 587. |

---

## 3. Supported Email Service Providers

### Option A: SendGrid
1. Create a SendGrid account at [sendgrid.com](https://sendgrid.com).
2. Complete **Sender Identity Verification** (Domain Authentication recommended).
3. Navigate to **Settings -> API Keys** and generate a key with **Mail Send** permissions.
4. Set in `.env`:
   ```env
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=SG.your_api_key_here
   SMTP_FROM_EMAIL=notifications@yourdomain.com
   SMTP_TLS=true
   ```

### Option B: Amazon Simple Email Service (SES)
1. In the AWS Management Console, navigate to **Amazon SES**.
2. Verify your domain name under **Configuration -> Verified Identities**.
3. Under **Account dashboard**, request production access (out of sandbox).
4. Create SMTP Credentials under **SMTP Settings -> Create SMTP Credentials**.
5. Set in `.env`:
   ```env
   SMTP_HOST=email-smtp.us-east-1.amazonaws.com
   SMTP_PORT=587
   SMTP_USERNAME=AKIAXXXXXXXXXXXXXXXX
   SMTP_PASSWORD=your_ses_smtp_password
   SMTP_FROM_EMAIL=noreply@yourdomain.com
   SMTP_TLS=true
   ```

### Option C: Google Workspace / Gmail (Development Testing)
1. Enable 2-Step Verification on your Google Account.
2. Generate an **App Password** (16 characters) under Google Account Security.
3. Set in `.env`:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   SMTP_FROM_EMAIL=your_email@gmail.com
   SMTP_TLS=true
   ```

---

## 4. Local Testing Procedure

Run the automated auth & email dispatch test suite:
```bash
pytest backend/tests/test_email_and_auth_phase3.py -v
```
