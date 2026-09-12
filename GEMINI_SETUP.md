# Google Gemini AI Setup Guide — SmartResume.ai

SmartResume.ai utilizes **Google Gemini models** to provide intelligent ATS parsing, deterministic fit gap analysis, STAR bullet formulation, and mock interview questions.

---

## 1. Supported Models
SmartResume.ai is configured to use Google's official Gemini models:
- **Default High-Capacity Model**: `gemini-3.6-flash` (or `gemini-1.5-flash` / `gemini-2.0-flash`)
- **Cost-Optimized / High-Throughput Model**: `gemini-3.5-flash-lite` (or `gemini-1.5-flash-8b`)

---

## 2. Obtaining a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API Key** in the top navigation or sidebar.
4. Select **Create API Key in new project** (or select an existing Google Cloud project).
5. Copy the generated key.

---

## 3. Configuring the Backend Environment
Open `backend/.env` and configure your API key:

```env
GEMINI_API_KEY=AIzaSyYourGeneratedGeminiApiKeyHere
GEMINI_MODEL=gemini-3.6-flash
GEMINI_LITE_MODEL=gemini-3.5-flash-lite
```

---

## 4. Local Deterministic Fallback Mode
SmartResume.ai includes a built-in **deterministic fallback engine**:
- If `GEMINI_API_KEY` is not provided or if Google AI APIs encounter rate-limits (`429 Quota Exceeded`), SmartResume.ai **gracefully falls back** to local rule-based AST and keyword matching.
- **Zero user-facing crashes**: ATS fit analysis, evidence mapping, and STAR formatting continue to work reliably even in offline/demo environments.

---

## 5. Verifying Gemini Connectivity
Run the following test in PowerShell to verify your key:

```powershell
python -c "from app.core.config import get_settings; import google.generativeai as genai; s = get_settings(); genai.configure(api_key=s.gemini_api_key); m = genai.GenerativeModel(s.gemini_model); res = m.generate_content('Hello, confirm connection in 3 words'); print('Gemini Response:', res.text)"
```
