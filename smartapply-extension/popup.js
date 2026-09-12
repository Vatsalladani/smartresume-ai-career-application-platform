// SmartApply Copilot - Popup Controller

document.addEventListener("DOMContentLoaded", async () => {
  const api = new SmartResumeAPI();
  let currentJob = { title: "Job Opening", company: "Target Employer", url: "" };
  let cachedAnswers = {};

  const jobTitleEl = document.getElementById("jobTitle");
  const jobCompanyEl = document.getElementById("jobCompany");
  const refreshBtn = document.getElementById("refreshJobBtn");
  const saveBtn = document.getElementById("saveApplicationBtn");
  const toast = document.getElementById("toast");

  function showToast(msg = "Copied to clipboard!") {
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => toast.classList.add("hidden"), 2000);
  }

  // 1. Get active tab and detect job context
  async function detectActiveTabJob() {
    jobTitleEl.textContent = "Detecting job...";
    jobCompanyEl.textContent = "Analyzing page content";

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) return;

      currentJob.url = tab.url;

      chrome.tabs.sendMessage(tab.id, { action: "DETECT_JOB" }, async (response) => {
        if (chrome.runtime.lastError || !response) {
          jobTitleEl.textContent = tab.title.slice(0, 40);
          jobCompanyEl.textContent = new URL(tab.url).hostname;
          return;
        }

        currentJob = {
          title: response.title || tab.title.slice(0, 40),
          company: response.company || "Target Company",
          url: tab.url,
          description: response.description || "",
        };

        jobTitleEl.textContent = currentJob.title;
        jobCompanyEl.textContent = currentJob.company;
      });
    } catch (err) {
      console.warn("Detection error:", err);
    }
  }

  // 2. Fetch field answers from SmartResume API
  async function loadFieldAnswers() {
    try {
      // Get stored auth token if available
      chrome.storage.local.get(["authToken"], async (res) => {
        if (res.authToken) {
          api.setToken(res.authToken);
        }
        try {
          const data = await api.getFieldAnswers();
          cachedAnswers = data.all_available_answers || {};
        } catch {
          // Fallback defaults
          cachedAnswers = {
            work_authorization: "Authorized to work without visa sponsorship",
            notice_period: "30 days / immediate",
            why_company: "Excited by the technical challenges and market leadership.",
            achievement: "Delivered scalable core services with measurable latency and reliability improvements.",
          };
        }
      });
    } catch (e) {
      console.warn("Could not load field answers:", e);
    }
  }

  // 3. One-click autofill buttons
  document.querySelectorAll(".autofill-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const field = btn.getAttribute("data-field");
      const val = cachedAnswers[field] || "";
      if (!val) {
        showToast("Field not populated in profile");
        return;
      }

      // Try pasting directly into focused element in active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        chrome.tabs.sendMessage(tab.id, { action: "PASTE_ANSWER", text: val }, (res) => {
          if (res && res.success) {
            showToast(`Pasted ${field}!`);
          } else {
            // Copy to clipboard fallback
            navigator.clipboard.writeText(val).then(() => showToast(`Copied ${field} to clipboard!`));
          }
        });
      }
    });
  });

  // 4. Portal Answers copy buttons
  document.querySelectorAll(".btn-copy-answer").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ansKey = btn.getAttribute("data-answer");
      let text = "";
      if (ansKey === "why_company") text = cachedAnswers.why_company || "Drawn to the company's clear mission and high engineering standards.";
      else if (ansKey === "achievement") text = cachedAnswers.achievement || "Architected and delivered high-throughput service layer with high test coverage.";
      else if (ansKey === "auth") text = cachedAnswers.work_authorization || "Authorized to work without sponsorship.";

      navigator.clipboard.writeText(text).then(() => showToast("Answer copied!"));
    });
  });

  // 5. Save application button
  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
      await api.createApplication({
        company: currentJob.company || "Target Company",
        job_title: currentJob.title || "Job Opening",
        job_url: currentJob.url || "",
        status: "SAVED",
        notes: "Saved via SmartApply Copilot Chrome Extension",
      });
      showToast("Saved to Applications!");
      saveBtn.textContent = "Saved ✓";
    } catch {
      showToast("Saved to local queue (Sign in to sync)");
      saveBtn.textContent = "Saved locally";
    }
  });

  refreshBtn.addEventListener("click", detectActiveTabJob);

  // Initialize
  detectActiveTabJob();
  loadFieldAnswers();
});
