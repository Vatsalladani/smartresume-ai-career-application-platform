// SmartApply Copilot - Content Script
// Non-invasive job page context detector and assistant

(function () {
  console.log("SmartApply Copilot content script active.");

  // Detect job details on the current webpage
  function detectJobDetails() {
    const url = window.location.href;
    let title = "";
    let company = "";
    let description = "";

    // 1. LinkedIn Job Posting
    if (url.includes("linkedin.com")) {
      const titleEl = document.querySelector(".job-details-jobs-unified-top-card__job-title, .topcard__title, h1");
      const companyEl = document.querySelector(".job-details-jobs-unified-top-card__company-name, .topcard__org-name-link, .job-details-jobs-unified-top-card__primary-description a");
      const descEl = document.querySelector(".jobs-description__content, #job-details");

      if (titleEl) title = titleEl.innerText.trim();
      if (companyEl) company = companyEl.innerText.trim();
      if (descEl) description = descEl.innerText.trim();
    }
    // 2. Indeed Job Posting
    else if (url.includes("indeed.com")) {
      const titleEl = document.querySelector("h1.jobsearch-JobInfoHeader-title, h1");
      const companyEl = document.querySelector("[data-testid='inlineHeader-companyName'], .jobsearch-CompanyInfoContainer a");
      const descEl = document.querySelector("#jobDescriptionText");

      if (titleEl) title = titleEl.innerText.trim();
      if (companyEl) company = companyEl.innerText.trim();
      if (descEl) description = descEl.innerText.trim();
    }
    // 3. Greenhouse Job Board
    else if (url.includes("greenhouse.io")) {
      const titleEl = document.querySelector(".app-title, h1");
      const companyEl = document.querySelector(".company-name");
      const descEl = document.querySelector("#content");

      if (titleEl) title = titleEl.innerText.trim();
      if (companyEl) company = companyEl.innerText.trim();
      if (descEl) description = descEl.innerText.trim();
    }
    // 4. Lever Job Board
    else if (url.includes("lever.co")) {
      const titleEl = document.querySelector(".posting-headline h2, h2");
      const descEl = document.querySelector(".section-wrapper");

      if (titleEl) title = titleEl.innerText.trim();
      if (descEl) description = descEl.innerText.trim();
    }
    // 5. Generic fallback
    if (!title) {
      const h1 = document.querySelector("h1");
      title = h1 ? h1.innerText.trim() : document.title;
    }
    if (!description) {
      const main = document.querySelector("main, article, [role='main']");
      description = main ? main.innerText.trim().slice(0, 5000) : document.body.innerText.trim().slice(0, 3000);
    }

    return {
      url,
      title: title.slice(0, 150),
      company: company.slice(0, 150),
      description: description.slice(0, 10000),
    };
  }

  // Listen for messages from extension popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "DETECT_JOB") {
      const details = detectJobDetails();
      sendResponse(details);
      return false;
    }

    if (request.action === "PASTE_ANSWER") {
      // Find active element or focused input
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.isContentEditable)) {
        if (activeEl.isContentEditable) {
          activeEl.innerText = request.text;
        } else {
          activeEl.value = request.text;
          activeEl.dispatchEvent(new Event("input", { bubbles: true }));
          activeEl.dispatchEvent(new Event("change", { bubbles: true }));
        }
        sendResponse({ success: true });
      } else {
        sendResponse({ success: false, error: "No input field currently focused" });
      }
      return false;
    }
  });
})();
