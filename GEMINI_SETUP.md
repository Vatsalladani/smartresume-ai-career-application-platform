# Google Gemini Live API Configuration Guide — SmartResume.ai

This document provides instructions for configuring and verifying Google Gemini models and the real-time **Gemini Live API** for SmartResume.ai's Live AI Interview Copilot.

---

## 1. Prerequisites & API Key Generation

1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API Key** and create an API key in a project with Gemini 2.0 / multimodal capabilities enabled.
4. Keep the key secure. **Never commit the API key to source control or hardcode it in repository files.**

---

## 2. Environment Variables Configuration

In the `backend/.env` file (or your environment configuration), add or update the following variables:

```ini
# Google Gemini Core Configuration
GEMINI_API_KEY=AIzaSy...your_actual_key_here
GEMINI_MODEL_NAME=gemini-3.6-flash
GEMINI_LITE_MODEL_NAME=gemini-3.5-flash-lite

# Google Gemini Live API Model Configuration
GEMINI_LIVE_MODEL_NAME=gemini-2.0-flash-exp
```

### Supported Live Models:
- `gemini-2.0-flash-exp` (Default recommended for low-latency bidirectional multimodal streaming)
- `gemini-2.0-flash-thinking-exp` (Deep reasoning)

---

## 3. Local Verification

To verify that the backend recognizes your Gemini configuration:

1. Restart the backend service:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Check the Live configuration endpoint:
   ```bash
   curl -H "Authorization: Bearer <your_jwt_token>" http://127.0.0.1:8000/api/v1/interview/live-config
   ```
   **Expected Response (When configured):**
   ```json
   {
     "success": true,
     "message": "Gemini Live API is ready.",
     "data": {
       "configured": true,
       "model_name": "gemini-2.0-flash-exp",
       "message": "Gemini Live API is ready."
     }
   }
   ```
   **Expected Response (When not configured):**
   ```json
   {
     "success": true,
     "message": "Live AI Interview is not configured yet. Configure GEMINI_API_KEY in backend/.env.",
     "data": {
       "configured": false,
       "model_name": null,
       "message": "Live AI Interview is not configured yet. Configure GEMINI_API_KEY in backend/.env."
     }
   }
   ```

---

## 4. Frontend Experience & Privacy Boundaries

1. **Stateful Fallback**: If `GEMINI_API_KEY` is not present, the user is presented with a clear banner: *"Live AI Interview is not configured yet."* alongside a `[Configure Gemini]` guide modal. The app never fakes live AI speech or pretends a real session is connected.
2. **Explicit Permission Flow**: Camera and microphone are **never** started automatically. Access is only requested via `navigator.mediaDevices.getUserMedia` when the candidate explicitly clicks `[Start Live Interview]`.
3. **Instant Media Teardown**: Whenever the user clicks `[End Interview]`, switches workspace tabs, or closes the browser, all tracks (`track.stop()`) are immediately terminated.
4. **Strict Ethical Boundaries**: Video input is used exclusively for candidate practice, framing, and lighting checks. The system never infers race, gender, age, religion, health, or personality from facial appearance.

---

## 5. Production Deployment Requirements

For production environments:
- Serve the frontend over **HTTPS** (browsers strictly require HTTPS for `getUserMedia` outside `localhost`).
- Use secure WebSocket (`wss://`) or WebRTC connections for bidirectional real-time audio streaming.
- Route requests through authenticated backend proxies to avoid exposing API keys to browser clients.

---

## 6. Rate Limits & Pricing Notes

- **Google AI Studio (Free Tier)**:
  - Subject to Requests Per Minute (RPM) and Tokens Per Minute (TPM) limits (typically 15 RPM for experimental models).
  - Rate-limited sessions should fall back cleanly or present user retry notifications.
- **Pay-as-you-go (Vertex AI / AI Studio Paid Tier)**:
  - Audio input/output and real-time multimodal tokens are billed according to Google Cloud Gemini pricing.
  - Gemini 2.0 Flash features ultra-competitive pricing ($0.10 / 1M input tokens; $0.40 / 1M output tokens for text; audio streaming billed at multimodal rates).
  - Cost monitoring and quota alerts should be configured in the Google Cloud Console.

