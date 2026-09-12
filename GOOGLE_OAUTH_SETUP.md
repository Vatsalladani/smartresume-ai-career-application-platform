# Google OAuth 2.0 Setup Guide — SmartResume.ai

This guide details how to configure Google OAuth 2.0 Single Sign-On (SSO) for SmartResume.ai.

---

## 1. Google Cloud Console Setup

### 1.1 Create or Select a Project
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top and select **New Project**.
3. Name your project (e.g., `SmartResume-AI-Production`) and click **Create**.

---

## 2. Configure OAuth Consent Screen

1. In the left navigation menu, go to **APIs & Services** → **OAuth consent screen**.
2. Select **External** user type and click **Create**.
3. Fill in the **App Information**:
   - **App name**: `SmartResume.ai`
   - **User support email**: Select your developer/admin email.
   - **App logo**: (Optional in development, recommended in production).
   - **Application home page**: `http://localhost:8000` (or your production URL).
   - **Authorized domains**: `localhost` (or your domain e.g., `smartresume.ai`).
   - **Developer contact information**: Your contact email.
4. Click **Save and Continue**.

### 2.2 Scopes
Click **Add or Remove Scopes** and select:
- `.../auth/userinfo.email` (See your primary Google Account email address)
- `.../auth/userinfo.profile` (See your personal info, including any personal info you've made publicly available)
- `openid` (Associate you with your personal info on Google)

Click **Save and Continue**.

### 2.3 Test Users (Development Mode)
While the app status is "Testing", add test Google accounts that will test the sign-in flow.
In production, submit the OAuth consent screen for Google verification.

---

## 3. Create OAuth 2.0 Client Credentials

1. Go to **APIs & Services** → **Credentials**.
2. Click **+ Create Credentials** → **OAuth client ID**.
3. **Application type**: Select **Web application**.
4. **Name**: `SmartResume Web Client`.
5. **Authorized JavaScript origins**:
   - `http://localhost:8000`
   - `https://your-domain.com` (for production)
6. **Authorized redirect URIs**:
   - `http://localhost:8000/api/v1/auth/google/callback`
   - `https://your-domain.com/api/v1/auth/google/callback`
7. Click **Create**.
8. A modal appears displaying your **Client ID** and **Client Secret**.

---

## 4. Backend Environment Configuration

Add the credentials into `backend/.env`:

```env
GOOGLE_CLIENT_ID=1234567890-abcdefg123456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-yourClientSecretKeyHere
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

---

## 5. Authentication Flow & Account Linking

When a user clicks **Continue with Google**:
1. Frontend redirects user to `GET /api/v1/auth/google/login`.
2. Backend generates a cryptographically random `state` nonce and redirects to Google's authorization endpoint:
   `https://accounts.google.com/o/oauth2/v2/auth?...`
3. Upon user authorization, Google redirects to `GET /api/v1/auth/google/callback?code=...&state=...`.
4. Backend exchanges the authorization code for an access token, fetches the user profile from Google UserInfo API:
   - If user exists with the matching email, the account is linked and marked `is_verified=True`.
   - If user does not exist, a new account is automatically created and an empty Master Profile is provisioned.
5. Backend issues a standard SmartResume.ai JWT access token and redirects the browser to the application dashboard with the session token.
