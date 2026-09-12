# LinkedIn OAuth 2.0 (OpenID Connect) Setup Guide — SmartResume.ai

This guide details how to configure LinkedIn Single Sign-On (SSO) using LinkedIn's OpenID Connect API for SmartResume.ai.

---

## 1. LinkedIn Developer Portal Setup

### 1.1 Create App
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Log in with your LinkedIn account.
3. Click **Create App**.
4. Fill in the app information:
   - **App name**: `SmartResume.ai`
   - **LinkedIn Page**: Associate your company page (or create a developer page if required).
   - **App logo**: Upload your square application logo.
   - **Legal terms**: Check the agreement checkbox.
5. Click **Create app**.

---

## 2. Request Products & Permissions

1. In the app dashboard, navigate to the **Products** tab.
2. Find **Sign In with LinkedIn using OpenID Connect**.
3. Click **Request access** and accept the terms.
4. Once approved (instant for OpenID Connect), the following permissions are granted under the **Auth** tab:
   - `openid` (Use your LinkedIn name and photo)
   - `profile` (Use your primary email address)
   - `email` (Associate your identity with OpenID Connect)

---

## 3. Configure OAuth 2.0 Settings

1. In the left navigation, click the **Auth** tab.
2. Scroll to **OAuth 2.0 settings**.
3. Under **Authorized redirect URLs for your app**, click the edit icon (or **+ Add redirect URL**).
4. Add your callback URLs:
   - Development: `http://localhost:8000/api/v1/auth/linkedin/callback`
   - Production: `https://your-domain.com/api/v1/auth/linkedin/callback`
5. Click **Update**.
6. Under **Application credentials**, copy your **Client ID** and **Primary Client Secret**.

---

## 4. Backend Environment Configuration

Add the credentials to `backend/.env`:

```env
LINKEDIN_CLIENT_ID=78xxxxxxxxxxxx
LINKEDIN_CLIENT_SECRET=WPL_AP1_xxxxxxxxxxxx
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/auth/linkedin/callback
```

---

## 5. Security & Platform Compliance

> [!IMPORTANT]
> **Strict Anti-Scraping & Platform Compliance**
> 
> SmartResume.ai strictly complies with LinkedIn's Developer Terms of Service and Anti-Scraping guidelines:
> - **No Background Scraping**: SmartResume.ai never scrapes candidate or job poster data from LinkedIn's web pages.
> - **No Headless Bots**: We do not inject auto-clicking or auto-applying bots into LinkedIn.
> - **Official APIs Only**: Candidate identity is retrieved solely via authorized OpenID Connect endpoints (`https://api.linkedin.com/v2/userinfo`).
> - **Candidate Consent**: All profile imports are user-initiated and require explicit permission.
