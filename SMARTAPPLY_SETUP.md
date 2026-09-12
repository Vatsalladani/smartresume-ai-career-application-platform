# SmartApply Copilot — Chrome Extension (Manifest V3) Setup & Architecture

SmartApply Copilot is an evidence-grounded browser companion that assists candidates in answering job portal screening questions accurately, pulling directly from their verified **Master Profile** and **Evidence Vault**.

---

## 1. Extension Architecture & Ethical Compliance

SmartApply Copilot is explicitly engineered with ethical, candidate-in-the-loop principles:

- **Manifest V3 Compliant**: Built on modern Chromium Manifest V3 standards with declarative permissions and secure background service workers.
- **No Unauthorized DOM Scraping**: Does not scrape proprietary job portal data or steal employer information.
- **No Auto-Submitting Bots**: Never submits job applications headlessly or without candidate review. Every answer is displayed for the candidate to review, approve, or refine before pasting.
- **Zero Hallucinations / Anti-Fabrication**: Answers are synthesized strictly from the candidate's verified evidence items and experience entries.

### Extension File Structure (`smartapply-extension/`)
```
smartapply-extension/
├── manifest.json       # Manifest V3 configuration & permissions
├── background.js       # Background service worker & auth token management
├── content.js          # Non-intrusive floating assistance pill & modal
├── api_client.js       # Authenticated communication with SmartResume.ai backend
├── popup.html          # Extension popup UI
├── popup.css           # Modern Tailwind-inspired styling
└── popup.js            # Popup controller for authentication and status check
```

---

## 2. Installation Instructions (Developer Mode)

You can load the extension into any Chromium-based browser (Google Chrome, Microsoft Edge, Brave, Arc, Opera):

1. Open your browser and navigate to the extensions page:
   - **Chrome**: `chrome://extensions`
   - **Edge**: `edge://extensions`
   - **Brave**: `brave://extensions`
2. Toggle on **Developer mode** (usually located in the top-right corner).
3. Click the **Load unpacked** button.
4. In the folder picker dialog, select the extension folder:
   `E:\RESUME SaaS ANTIGRAVITY\smartapply-extension`
5. Click **Select Folder**.
6. The **SmartResume.ai SmartApply Copilot** card will now appear in your active extensions list!

---

## 3. Connecting to Your Account

1. Ensure the SmartResume.ai backend is running (`http://localhost:8000`).
2. Click the puzzle icon in your browser toolbar to locate **SmartApply Copilot**, then pin it to your toolbar.
3. Click the SmartApply Copilot icon.
4. Enter your SmartResume.ai **Email** and **Password** (or paste an active JWT access token).
5. Click **Connect Account**.
6. Once connected, your verified candidate name, plan status, and evidence count will appear in the popup.

---

## 4. Usage Workflow on Job Portals

When filling out applications on Greenhouse, Lever, Workday, Taleo, LinkedIn, Indeed, or company careers pages:

1. **Floating Copilot Pill**: A discreet, floating **"SmartApply Copilot"** widget appears on supported application pages.
2. **Select or Type Question**: Click the widget to expand it. Enter or paste the portal question (e.g., *"Describe a time you solved a complex technical bottleneck"* or *"Why are you interested in this role?"*).
3. **Select Tone**: Choose between **Professional**, **Direct/Crisp**, or **Technical**.
4. **Generate Evidence-Grounded Answer**: Click **Generate Answer**. SmartResume.ai queries your Evidence Vault to produce a tailored, STAR-formatted answer citing your real projects.
5. **Review & Copy**: Review the generated answer in the modal. Click **Copy to Clipboard** or click **SmartFill Field** to insert it into the active text area.
6. **Submit Manually**: The user retains complete agency to review and manually submit their application.
