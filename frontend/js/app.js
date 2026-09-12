// SmartResume.ai SPA Application Controller — Production-Grade MVP
const state = {
  user: null,
  profile: null,
  jobs: [],
  activeJob: null,
  lastFitResult: null,
  lastTailoringProposal: null,
  tailoredBulletsState: [], // [{ id, exp_id, original, tailored, change_type, accepted }]
  versions: [],
  activeVersion: null,
  applications: [],
  quotas: null,
  importDraft: null,
  selectedCurrency: "INR",
  pricingData: null,
  paymentHistory: [],
  oauthConfig: null,
  pendingPlanKey: null,
  templates: [],
  activeTemplateId: localStorage.getItem("activeTemplateId") || "classic_ats",
  selectedCompareIds: new Set(),
  templateIntent: "ALL",
  templateCategory: "ALL",
  templateTier: "ALL",
  templateSearch: "",
  templateRecommendation: null,
  customizer: {
    fontSize: "medium",
    spacing: "standard",
    accentColor: "#1e3a8a",
  },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

document.addEventListener("DOMContentLoaded", () => {
  wireTheme();
  wireAuth();
  wireNavigation();
  wireMasterProfile();
  wireJobFit();
  wireTailoringStudio();
  wireApplications();
  wireBilling();
  wireSettings();
  wireIntelligenceModals();
  wireOnboardingModal();
  wireEvidenceVault();
  wireTemplates();
  wireJobRadar();
  wireSmartApplyTab();
  wireInterviewCopilot();
  wireCareerInsights();
  wireNotifications();
  wireProTrial();
  wireInternationalRules();
  wireApplicationPackModal();
  wireGuidanceSystem();
  boot();
});

// Boot & Lifecycle
async function boot() {
  document.documentElement.dataset.theme = localStorage.getItem("theme") || "light";

  // Check for OAuth Callback query params in URL
  const urlParams = new URLSearchParams(window.location.search);
  const oauthCode = urlParams.get("code");
  const oauthProvider = urlParams.get("provider") || (window.location.pathname.includes("google") ? "google" : "linkedin");

  if (oauthCode) {
    await handleOAuthCallback(oauthCode, oauthProvider);
    return;
  }

  if (API.getAccessToken()) {
    await loadApp();
  } else {
    showAuth();
  }
  drawIcons();
}

function drawIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function toast(message, type = "info") {
  const host = $("#toastHost");
  if (!host) return;
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.textContent = message;
  host.appendChild(node);
  setTimeout(() => node.remove(), 4500);
}

function showAuth(mode = "login") {
  $("#authView").classList.remove("hidden");
  $("#appView").classList.add("hidden");
  setAuthMode(mode);
}

function showApp() {
  $("#authView").classList.add("hidden");
  $("#appView").classList.remove("hidden");
}

function setAuthMode(mode) {
  const titles = {
    login: "Welcome back",
    register: "Create your SmartResume account",
    forgot: "Reset your password",
    reset: "Set a new secure password",
  };
  $("#authSubtitle").textContent = titles[mode] || "Welcome back";
  ["login", "register", "forgot", "reset"].forEach((name) => {
    const form = $(`#${name}Form`);
    if (form) form.classList.toggle("hidden", name !== mode);
    const footer = $(`#authFooter${capitalize(name)}`);
    if (footer) footer.classList.toggle("hidden", name !== mode);
  });

  const oauthGroup = $("#oauthActionGroup");
  const oauthDivider = $(".oauth-divider");
  const showOAuth = (mode === "login" || mode === "register");
  if (oauthGroup) oauthGroup.classList.toggle("hidden", !showOAuth);
  if (oauthDivider) oauthDivider.classList.toggle("hidden", !showOAuth);

  drawIcons();
}

function wireTheme() {
  const toggle = $("#themeToggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("theme", next);
    });
  }
}

// AUTHENTICATION & SOCIAL OAUTH 2.0
function wireAuth() {
  $$("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
  });

  // Google OAuth button
  $("#googleOAuthBtn").addEventListener("click", async () => {
    try {
      const config = await API.request("/auth/oauth/config", { auth: false });
      state.oauthConfig = config;
      if (config.google?.configured || config.google_enabled) {
        const urlData = await API.request("/auth/oauth/google/url", { auth: false });
        window.location.href = urlData.url;
      } else {
        openOAuthModal("Google OAuth Setup", config.google?.instructions || "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable Google 1-click authentication.");
      }
    } catch (err) {
      openOAuthModal("Google OAuth Notice", "Google OAuth 2.0 backend endpoints are mounted. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file to enable live sign-in.");
    }
  });

  // LinkedIn OAuth button
  $("#linkedinOAuthBtn").addEventListener("click", async () => {
    try {
      const config = await API.request("/auth/oauth/config", { auth: false });
      state.oauthConfig = config;
      if (config.linkedin?.configured || config.linkedin_enabled) {
        const urlData = await API.request("/auth/oauth/linkedin/url", { auth: false });
        window.location.href = urlData.url;
      } else {
        openOAuthModal("LinkedIn OAuth Setup", config.linkedin?.instructions || "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env to enable LinkedIn 1-click authentication.");
      }
    } catch (err) {
      openOAuthModal("LinkedIn OAuth Notice", "LinkedIn OAuth 2.0 backend endpoints are mounted. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in your .env file to enable live sign-in.");
    }
  });

  // OAuth Modal close buttons
  $("#closeOAuthModalBtn").addEventListener("click", () => $("#oauthModal").classList.add("hidden"));
  $("#dismissOAuthModalBtn").addEventListener("click", () => $("#oauthModal").classList.add("hidden"));

  // Standard Email Login
  $("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const btn = $("#loginForm button[type='submit']");
    setButtonLoading(btn, true, "Signing in...");
    try {
      const data = await API.request("/auth/login", {
        method: "POST",
        auth: false,
        body: { email: $("#loginEmail").value, password: $("#loginPassword").value },
      });
      API.setSession(data);
      toast("Welcome back!");
      await loadApp();
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(btn, false, "Sign In");
    }
  });

  // Register Form
  $("#registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const btn = $("#registerForm button[type='submit']");
    const password = $("#registerPassword").value;
    const confirmPassword = $("#registerConfirmPassword") ? $("#registerConfirmPassword").value : password;

    if (password !== confirmPassword) {
      toast("Passwords do not match. Please verify and try again.", "error");
      return;
    }

    setButtonLoading(btn, true, "Creating account...");
    try {
      await API.request("/auth/register", {
        method: "POST",
        auth: false,
        body: {
          full_name: $("#registerName").value,
          email: $("#registerEmail").value,
          password: password,
        },
      });
      toast("Account created! Please sign in with your credentials.");
      setAuthMode("login");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(btn, false, "Create Free Account");
    }
  });

  // Forgot Password
  $("#forgotForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const btn = $("#forgotForm button[type='submit']");
    setButtonLoading(btn, true, "Sending request...");
    try {
      await API.request("/auth/forgot-password", {
        method: "POST",
        auth: false,
        body: { email: $("#forgotEmail").value },
      });
      toast("If that email exists, reset instructions were generated.");
      setAuthMode("reset");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(btn, false, "Request Password Reset");
    }
  });

  // Reset Password
  $("#resetForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const btn = $("#resetForm button[type='submit']");
    const newPassword = $("#resetPassword").value;
    const confirmNewPassword = $("#resetConfirmPassword") ? $("#resetConfirmPassword").value : newPassword;

    if (newPassword !== confirmNewPassword) {
      toast("Passwords do not match. Please verify and try again.", "error");
      return;
    }

    setButtonLoading(btn, true, "Resetting password...");
    try {
      await API.request("/auth/reset-password", {
        method: "POST",
        auth: false,
        body: { token: $("#resetToken").value, new_password: newPassword },
      });
      toast("Password reset successfully. Sign in with your new password.");
      setAuthMode("login");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(btn, false, "Set New Password");
    }
  });

  // Logout
  $("#logoutBtn").addEventListener("click", async () => {
    try {
      await API.request("/auth/logout", {
        method: "POST",
        body: { refresh_token: API.getRefreshToken() },
      });
    } catch (_) {}
    API.clearSession();
    showAuth();
  });
}

function openOAuthModal(title, message) {
  $("#oauthModalTitle").innerHTML = `<i data-lucide="key"></i> ${escapeHtml(title)}`;
  $("#oauthModalMessage").textContent = message;
  $("#oauthModal").classList.remove("hidden");
  drawIcons();
}

async function handleOAuthCallback(code, provider) {
  toast(`Exchanging authorization with ${capitalize(provider)}...`);
  try {
    const endpoint = provider === "google" ? "/auth/oauth/google/callback" : "/auth/oauth/linkedin/callback";
    const data = await API.request(endpoint, {
      method: "POST",
      auth: false,
      body: { code },
    });
    API.setSession(data);
    window.history.replaceState({}, document.title, window.location.pathname);
    toast("Authenticated successfully!");
    await loadApp();
  } catch (error) {
    toast(`OAuth failed: ${error.message}`, "error");
    window.history.replaceState({}, document.title, window.location.pathname);
    showAuth();
  }
}

const ROUTES = {
  "#/dashboard": "dashboard",
  "#/career-profile": "profile",
  "#/evidence": "evidence-vault",
  "#/templates": "templates",
  "#/job-radar": "job-radar",
  "#/job-match": "fit",
  "#/application-builder": "tailor",
  "#/smartapply": "smartapply",
  "#/applications": "applications",
  "#/interview": "interview",
  "#/insights": "career-insights",
  "#/billing": "billing",
  "#/settings": "settings",
};

const TAB_TO_ROUTE = {
  "dashboard": "#/dashboard",
  "profile": "#/career-profile",
  "evidence-vault": "#/evidence",
  "templates": "#/templates",
  "job-radar": "#/job-radar",
  "fit": "#/job-match",
  "tailor": "#/application-builder",
  "smartapply": "#/smartapply",
  "applications": "#/applications",
  "interview": "#/interview",
  "career-insights": "#/insights",
  "billing": "#/billing",
  "settings": "#/settings",
};

const TAB_MAP = {
  "dashboard": "tabDashboard",
  "profile": "tabProfile",
  "evidence-vault": "tabEvidenceVault",
  "templates": "tabTemplates",
  "job-radar": "tabJobRadar",
  "fit": "tabFit",
  "tailor": "tabApplicationBuilder",
  "smartapply": "tabSmartApply",
  "applications": "tabApplications",
  "interview": "tabInterview",
  "career-insights": "tabCareerInsights",
  "billing": "tabBilling",
  "settings": "tabSettings",
};

function wireNavigation() {
  function activateTab(tabName, updateHash = true) {
    const validTab = TAB_MAP[tabName] ? tabName : "dashboard";

    // 1. Highlight sidebar navigation item
    $$(".nav-tabs button").forEach((item) => {
      if (item.dataset.tab === validTab) {
        item.classList.add("active");
        item.setAttribute("aria-selected", "true");
        const label = item.querySelector("span") ? item.querySelector("span").textContent.trim() : item.textContent.trim();
        const pageTitleEl = $("#pageTitle");
        if (pageTitleEl) pageTitleEl.textContent = label;
        document.title = `SmartResume.ai — ${label}`;
      } else {
        item.classList.remove("active");
        item.setAttribute("aria-selected", "false");
      }
    });

    // 2. Hide all workspaces and show only the active workspace
    $$(".tab-panel").forEach((panel) => panel.classList.remove("active"));
    const panelId = TAB_MAP[validTab];
    const targetPanel = $(`#${panelId}`) || $(`#${validTab}Tab`) || $(`#tab${capitalize(validTab)}`);
    if (targetPanel) {
      targetPanel.classList.add("active");
      window.scrollTo({ top: 0, behavior: "instant" });
    }

    // 3. Close mobile drawer
    closeMobileDrawer();

    // 4. Update browser URL hash for bookmarking & history navigation
    if (updateHash && TAB_TO_ROUTE[validTab]) {
      if (window.location.hash !== TAB_TO_ROUTE[validTab]) {
        window.history.pushState(null, "", TAB_TO_ROUTE[validTab]);
      }
    }

    // 5. Trigger view data refresh
    if (validTab === "templates") loadTemplatesView();
    if (validTab === "evidence-vault") loadEvidenceVault();
    if (validTab === "job-radar") loadJobRadar();
    if (validTab === "career-insights") loadCareerInsights();
    if (validTab === "interview") loadInterviewSessions();
    if (validTab === "smartapply") loadSmartApplyAnswers();
    if (validTab === "billing") {
      loadBillingSummary();
      loadPaymentHistory();
    }
    if (validTab === "dashboard") renderDashboard();

    drawIcons();
  }

  // Sidebar button click events
  $$(".nav-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      activateTab(button.dataset.tab, true);
    });
  });

  // Browser Back / Forward hash navigation
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash;
    const tabName = ROUTES[hash] || "dashboard";
    activateTab(tabName, false);
  });

  // Mobile drawer controls
  const mobileMenuBtn = $("#mobileMenuBtn");
  const backdrop = $("#sidebarBackdrop");

  function openMobileDrawer() {
    const sidebar = $(".sidebar");
    if (sidebar) sidebar.classList.add("mobile-open");
    if (backdrop) backdrop.classList.add("active");
  }

  function closeMobileDrawer() {
    const sidebar = $(".sidebar");
    if (sidebar) sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
  }

  if (mobileMenuBtn) mobileMenuBtn.addEventListener("click", openMobileDrawer);
  if (backdrop) backdrop.addEventListener("click", closeMobileDrawer);

  // Register tab activation handler
  _activateTabHandler = activateTab;
}

let _activateTabHandler = null;

function navigateToTab(tabName) {
  if (_activateTabHandler) {
    _activateTabHandler(tabName, true);
  } else {
    const btn = $(`[data-tab="${tabName}"]`);
    if (btn) btn.click();
  }
}
window.navigateToTab = navigateToTab;

function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : "";
}

function setButtonLoading(button, isLoading, text) {
  if (!button) return;
  button.disabled = isLoading;
  const span = button.querySelector("span");
  if (span) span.textContent = text;
  else button.textContent = text;
}

// APPLICATION DATA LOADING & ORCHESTRATION
async function loadApp() {
  try {
    showApp();
    state.user = await API.request("/users/profile");
    renderUserBar();
    await Promise.all([
      loadMasterProfile(),
      loadJobs(),
      loadApplications(),
      loadBillingSummary(),
      loadPricingData(),
      loadPaymentHistory(),
      loadNotifications(),
      loadTemplatesCatalogOnly(),
    ]);
    renderDashboard();
    drawIcons();
    const initialTab = ROUTES[window.location.hash] || "dashboard";
    navigateToTab(initialTab);
    checkAndShowOnboarding();
  } catch (error) {
    API.clearSession();
    toast(error.message, "error");
    showAuth();
  }
}

function renderUserBar() {
  if (!state.user) return;
  $("#profileLine").textContent = `${state.user.full_name} (${state.user.email})`;
  $("#planBadge").textContent = state.user.plan_name;
  if ($("#billingCurrentPlanBadge")) $("#billingCurrentPlanBadge").textContent = state.user.plan_name;
  $("#profileName").value = state.user.full_name;
  $("#profileEmail").value = state.user.email;
  $("#dashWelcomeName").textContent = `Welcome back, ${state.user.full_name}!`;

  // Check 7-Day Pro Trial Banner
  const trialBanner = $("#trialBanner");
  if (state.user.plan_name === "PRO_TRIAL") {
    if (trialBanner) {
      trialBanner.classList.remove("hidden");
      const daysLeft = $("#trialDaysLeft");
      if (daysLeft) daysLeft.textContent = "Active (₹0 trial)";
    }
  } else if (trialBanner) {
    trialBanner.classList.add("hidden");
  }
}

// TAB 0: DASHBOARD RENDERING
function renderDashboard() {
  const p = state.profile || {};
  const score = p.completeness_score || 0;

  // 4 Core Questions in Dashboard
  const q1 = $("#dashQ1Answer");
  if (q1) {
    const verifiedCount = (p.skills || []).filter(s => s.evidence_status === "SUPPORTED").length;
    const totalSkills = (p.skills || []).length;
    q1.textContent = `Profile Health: ${score}/100 (${score >= 80 ? "Strong Evidence" : score >= 50 ? "Moderate" : "Needs Grounding"}). ${verifiedCount} of ${totalSkills} skills verified with project/experience evidence.`;
  }

  const q2 = $("#dashQ2Answer");
  if (q2) {
    if (state.jobs && state.jobs.length > 0) {
      q2.textContent = `${state.jobs.length} target role(s) being pursued. Active: ${state.jobs[0].title} at ${state.jobs[0].company}.`;
    } else {
      q2.textContent = "No target jobs analyzed yet. Paste a job description in Job Match & Fit.";
    }
  }

  const q3 = $("#dashQ3Answer");
  if (q3) {
    const missing = [];
    if (!p.experiences || p.experiences.length === 0) missing.push("Add work experiences");
    if (!p.skills || p.skills.length < 3) missing.push("Add verified skills");
    if (!p.projects || p.projects.length === 0) missing.push("Add key projects");
    if (missing.length > 0) {
      q3.textContent = `Priority actions: ${missing.join(", ")}. Grounding improves ATS alignment.`;
    } else {
      q3.textContent = "Strong foundational profile. Run Resume Health Report to inspect verb strength & density.";
    }
  }

  const q4 = $("#dashQ4Answer");
  if (q4) {
    if (state.applications && state.applications.length > 0) {
      const latest = state.applications[0];
      q4.textContent = `${state.applications.length} application(s) tracked. Latest: ${latest.job_title} at ${latest.company} [${latest.status}].`;
    } else if (state.versions && state.versions.length > 0) {
      q4.textContent = `${state.versions.length} immutable snapshot(s) generated. Link one in Application Tracker.`;
    } else {
      q4.textContent = "No tailored version snapshots linked yet. Generate in Tailoring Studio.";
    }
  }

  // Grounding meter
  $("#dashCompletenessPercent").textContent = `${score}%`;
  const circle = $("#dashMeterCircle");
  if (score >= 80) {
    circle.style.borderColor = "var(--success)";
    $("#dashCompletenessLabel").textContent = "Strong Evidence Grounding";
  } else if (score >= 50) {
    circle.style.borderColor = "var(--warning)";
    $("#dashCompletenessLabel").textContent = "Moderate Grounding";
  } else {
    circle.style.borderColor = "var(--primary)";
    $("#dashCompletenessLabel").textContent = "Action Recommended";
  }

  // Quotas in Dashboard
  if (state.quotas) {
    const q = state.quotas.quotas || {};
    const fits = q.fit_analyses || { used: 0, limit: 2 };
    const tailors = q.tailored_versions || { used: 0, limit: 2 };
    const exports_ = q.exports || { used: 0, limit: 2 };

    $("#dashFitsUsage").textContent = `${fits.used} / ${fits.limit}`;
    $("#dashFitsBar").style.width = `${Math.min(100, Math.round((fits.used / (fits.limit || 1)) * 100))}%`;

    $("#dashTailorsUsage").textContent = `${tailors.used} / ${tailors.limit}`;
    $("#dashTailorsBar").style.width = `${Math.min(100, Math.round((tailors.used / (tailors.limit || 1)) * 100))}%`;

    $("#dashExportsUsage").textContent = `${exports_.used} / ${exports_.limit}`;
    $("#dashExportsBar").style.width = `${Math.min(100, Math.round((exports_.used / (exports_.limit || 1)) * 100))}%`;
  }

  // Recent Applications on Dashboard
  const appContainer = $("#dashApplicationsList");
  appContainer.innerHTML = "";
  if (!state.applications || state.applications.length === 0) {
    appContainer.innerHTML = `
      <div class="empty-state-card mini">
        <i data-lucide="briefcase"></i>
        <p>No job applications tracked yet.</p>
        <button class="secondary-btn sm" type="button" onclick="navigateToTab('applications')">Add Application</button>
      </div>`;
  } else {
    state.applications.slice(0, 3).forEach((app) => {
      const card = document.createElement("div");
      card.className = "card-item";
      card.innerHTML = `
        <div class="card-item-header">
          <div>
            <strong>${escapeHtml(app.job_title)}</strong> <span class="text-muted">at ${escapeHtml(app.company)}</span>
          </div>
          <span class="badge-musthave">${escapeHtml(app.status)}</span>
        </div>
      `;
      appContainer.appendChild(card);
    });
  }

  // Recent Jobs on Dashboard
  const jobsContainer = $("#dashJobsList");
  jobsContainer.innerHTML = "";
  if (!state.jobs || state.jobs.length === 0) {
    jobsContainer.innerHTML = `
      <div class="empty-state-card mini">
        <i data-lucide="file-search"></i>
        <p>No target job postings analyzed yet.</p>
        <button class="secondary-btn sm" type="button" onclick="navigateToTab('fit')">Analyze First Job</button>
      </div>`;
  } else {
    state.jobs.slice(0, 3).forEach((job) => {
      const card = document.createElement("div");
      card.className = "card-item";
      card.innerHTML = `
        <div class="card-item-header">
          <div>
            <strong>${escapeHtml(job.title)}</strong> <span class="text-muted">at ${escapeHtml(job.company)}</span>
          </div>
          <button class="secondary-btn sm" type="button" data-open-job="${job.id}">View Fit</button>
        </div>
      `;
      card.querySelector(`[data-open-job="${job.id}"]`).addEventListener("click", () => {
        selectJob(job.id);
        navigateToTab("fit");
      });
      jobsContainer.appendChild(card);
    });
  }

  // Recent Activity Stream on Dashboard
  const actContainer = $("#dashRecentActivityList");
  if (actContainer) {
    actContainer.innerHTML = "";
    const activities = [];
    if (state.applications && state.applications.length > 0) {
      state.applications.slice(0, 3).forEach((app) => {
        activities.push({
          icon: "briefcase",
          title: `Application: ${app.job_title} at ${app.company}`,
          subtitle: `Status: ${app.status || "Applied"}`,
          date: app.applied_date || app.created_at ? new Date(app.applied_date || app.created_at).toLocaleDateString() : "Recent",
          actionTab: "applications",
        });
      });
    }
    if (state.jobs && state.jobs.length > 0) {
      state.jobs.slice(0, 3).forEach((job) => {
        activities.push({
          icon: "radar",
          title: `Target Job: ${job.title} at ${job.company}`,
          subtitle: `Analyzed with match intelligence`,
          date: job.created_at ? new Date(job.created_at).toLocaleDateString() : "Recent",
          actionTab: "fit",
        });
      });
    }
    if (state.profile?.updated_at) {
      activities.push({
        icon: "user-check",
        title: "Career Profile Updated",
        subtitle: `Profile health score: ${score}%`,
        date: new Date(state.profile.updated_at).toLocaleDateString(),
        actionTab: "profile",
      });
    }

    if (activities.length === 0) {
      actContainer.innerHTML = `
        <div class="empty-state-card mini">
          <i data-lucide="clock"></i>
          <p>No activity yet. Analyze a job or build your profile to see recent activity here.</p>
        </div>`;
    } else {
      activities.slice(0, 4).forEach((item) => {
        const row = document.createElement("div");
        row.className = "card-item";
        row.style.cursor = "pointer";
        row.innerHTML = `
          <div class="card-item-header">
            <div style="display: flex; align-items: center; gap: 10px;">
              <i data-lucide="${item.icon}"></i>
              <div>
                <strong>${escapeHtml(item.title)}</strong>
                <p class="text-xs text-muted">${escapeHtml(item.subtitle)}</p>
              </div>
            </div>
            <span class="text-xs text-muted">${escapeHtml(item.date)}</span>
          </div>
        `;
        row.addEventListener("click", () => navigateToTab(item.actionTab));
        actContainer.appendChild(row);
      });
    }
  }

  syncActiveTemplateDisplay();
  drawIcons();
}

// TAB 1: MASTER PROFILE
function wireMasterProfile() {
  $("#saveMasterProfileBtn").addEventListener("click", saveMasterProfileDetails);
  $("#openImportModalBtn").addEventListener("click", () => openImportModal());
  $("#closeImportModalBtn").addEventListener("click", () => closeImportModal());
  $("#cancelImportBtn").addEventListener("click", () => closeImportModal());

  // Dropzone for import
  const dropZone = $("#importDropZone");
  ["dragenter", "dragover"].forEach((evt) => {
    dropZone.addEventListener(evt, (e) => { e.preventDefault(); dropZone.classList.add("dragging"); });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dropZone.addEventListener(evt, () => dropZone.classList.remove("dragging"));
  });
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) {
      $("#importFileInput").files = e.dataTransfer.files;
      toast(`Selected: ${e.dataTransfer.files[0].name}`);
    }
  });

  $("#parseResumeBtn").addEventListener("click", parseResumeForImport);
  $("#commitImportBtn").addEventListener("click", commitImportDraft);

  // Experience modal
  $("#addExperienceBtn").addEventListener("click", () => openExperienceModal());
  $("#closeExpModalBtn").addEventListener("click", () => closeExperienceModal());
  $("#cancelExpBtn").addEventListener("click", () => closeExperienceModal());
  $("#experienceForm").addEventListener("submit", handleSaveExperience);

  // Project modal
  $("#addProjectBtn").addEventListener("click", () => openProjectModal());
  $("#closeProjModalBtn").addEventListener("click", () => closeProjectModal());
  $("#cancelProjBtn").addEventListener("click", () => closeProjectModal());
  $("#projectForm").addEventListener("submit", handleSaveProject);

  // Education modal
  $("#addEducationBtn").addEventListener("click", () => openEducationModal());
  $("#closeEduModalBtn").addEventListener("click", () => closeEducationModal());
  $("#cancelEduBtn").addEventListener("click", () => closeEducationModal());
  $("#educationForm").addEventListener("submit", handleSaveEducation);

  // Certification modal
  $("#addCertBtn").addEventListener("click", () => openCertModal());
  $("#closeCertModalBtn").addEventListener("click", () => closeCertModal());
  $("#cancelCertBtn").addEventListener("click", () => closeCertModal());
  $("#certForm").addEventListener("submit", handleSaveCert);

  // Inline skill form
  $("#addSkillForm").addEventListener("submit", handleAddSkill);

  // Health report & relevance checks
  $("#openHealthReportBtn")?.addEventListener("click", () => openHealthReportModal());
  $("#openRelevanceBtn")?.addEventListener("click", () => openRelevanceModal());
  $("#profCareerLevel")?.addEventListener("change", async (e) => {
    try {
      await API.request("/profile/career-level", { method: "POST", body: { career_level: e.target.value } });
      toast(`Career level updated: ${e.target.value.replace("_", " ")}`);
      await loadMasterProfile();
    } catch (err) {
      toast(err.message, "error");
    }
  });
  $("#profDomain")?.addEventListener("change", async (e) => {
    try {
      await API.request("/profile", { method: "PUT", body: { target_domain: e.target.value } });
      toast(`Target domain updated: ${e.target.value}`);
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function loadMasterProfile() {
  try {
    state.profile = await API.request("/profile");
    renderMasterProfile();
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderMasterProfile() {
  const p = state.profile;
  if (!p) return;

  // Contact / Headline fields
  $("#profHeadline").value = p.headline || "";
  $("#profSummary").value = p.summary || "";
  $("#profPhone").value = p.phone || "";
  $("#profLocation").value = p.location || "";
  $("#profLinkedIn").value = p.linkedin_url || "";
  $("#profGitHub").value = p.github_url || "";
  $("#profWebsite").value = p.portfolio_url || "";
  if (p.target_domain && $("#profDomain")) $("#profDomain").value = p.target_domain;
  if (p.career_level && $("#profCareerLevel")) $("#profCareerLevel").value = p.career_level;

  // Completeness Meter
  const score = p.completeness_score || 0;
  $("#completenessPercent").textContent = `${score}%`;
  const circle = $("#profileMeterCircle");
  if (score >= 80) circle.style.borderColor = "var(--success)";
  else if (score >= 50) circle.style.borderColor = "var(--warning)";
  else circle.style.borderColor = "var(--primary)";

  // Missing sections
  const missingHost = $("#missingSectionsList");
  missingHost.innerHTML = "";
  if (!p.experiences || p.experiences.length === 0) {
    missingHost.appendChild(createBadge("Missing: Work Experience", "missing-tag"));
  }
  if (!p.skills || p.skills.length < 3) {
    missingHost.appendChild(createBadge("Add at least 3 skills", "missing-tag"));
  }
  if (!p.headline) {
    missingHost.appendChild(createBadge("Missing: Headline", "missing-tag"));
  }
  if (!p.education || p.education.length === 0) {
    missingHost.appendChild(createBadge("Missing: Education", "missing-tag"));
  }

  // Render Sub-Lists
  renderExperiencesList(p.experiences || []);
  renderProjectsList(p.projects || []);
  renderEducationList(p.education || []);
  renderCertificationsList(p.certifications || []);
  renderSkillsList(p.skills || []);
  drawIcons();
}

function createBadge(text, className) {
  const span = document.createElement("span");
  span.className = className;
  span.textContent = text;
  return span;
}

async function saveMasterProfileDetails() {
  const btn = $("#saveMasterProfileBtn");
  setButtonLoading(btn, true, "Saving...");
  try {
    const payload = {
      headline: $("#profHeadline").value,
      summary: $("#profSummary").value,
      phone: $("#profPhone").value,
      location: $("#profLocation").value,
      linkedin_url: $("#profLinkedIn").value || null,
      github_url: $("#profGitHub").value || null,
      portfolio_url: $("#profWebsite").value || null,
      target_domain: $("#profDomain") ? $("#profDomain").value : undefined,
      career_level: $("#profCareerLevel") ? $("#profCareerLevel").value : undefined,
    };
    state.profile = await API.request("/profile", { method: "PUT", body: payload });
    toast("Master Profile details saved.");
    renderMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Save Master Profile");
  }
}

// EXPERIENCES
function renderExperiencesList(experiences) {
  const container = $("#experienceList");
  container.innerHTML = "";
  if (!experiences.length) {
    container.innerHTML = `
      <div class="empty-state-card">
        <i data-lucide="briefcase"></i>
        <h4>No work experience added</h4>
        <p>Add your past roles, metrics, and achievements to back your resume bullets with verified evidence.</p>
        <button class="secondary-btn sm" type="button" onclick="$('#addExperienceBtn').click()"><i data-lucide="plus"></i><span>Add Work Experience</span></button>
      </div>`;
    return;
  }
  experiences.forEach((exp) => {
    const card = document.createElement("div");
    card.className = "card-item";
    const bulletsHtml = (exp.bullet_points || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("");
    const techHtml = (exp.technologies_used || []).join(", ");

    card.innerHTML = `
      <div class="card-item-header">
        <div>
          <h4>${escapeHtml(exp.role_title)} <span class="text-muted">at</span> ${escapeHtml(exp.company)}</h4>
          <span class="text-xs text-muted">${escapeHtml(exp.start_date)} — ${exp.is_current ? "Present" : escapeHtml(exp.end_date || "")} ${exp.location ? "• " + escapeHtml(exp.location) : ""}</span>
        </div>
        <div class="card-actions">
          <button class="icon-btn sm" type="button" title="Delete" data-del-exp="${exp.id}"><i data-lucide="trash-2"></i></button>
        </div>
      </div>
      ${techHtml ? `<p class="text-xs mt-1"><strong>Tech:</strong> ${escapeHtml(techHtml)}</p>` : ""}
      <ul class="clean-list text-sm mt-2">${bulletsHtml}</ul>
    `;
    card.querySelector(`[data-del-exp="${exp.id}"]`).addEventListener("click", () => deleteExperience(exp.id));
    container.appendChild(card);
  });
}

function openExperienceModal(exp = null) {
  $("#experienceForm").reset();
  $("#expEditId").value = exp ? exp.id : "";
  $("#expModalTitle").textContent = exp ? "Edit Experience" : "Add Experience";
  if (exp) {
    $("#expCompany").value = exp.company;
    $("#expRole").value = exp.role_title;
    $("#expLocation").value = exp.location || "";
    $("#expType").value = exp.employment_type || "";
    $("#expStart").value = exp.start_date || "";
    $("#expEnd").value = exp.end_date || "";
    $("#expIsCurrent").checked = Boolean(exp.is_current);
    $("#expTech").value = (exp.technologies_used || []).join(", ");
    $("#expBullets").value = (exp.bullet_points || []).join("\n");
  }
  $("#experienceModal").classList.remove("hidden");
  drawIcons();
}

function closeExperienceModal() {
  $("#experienceModal").classList.add("hidden");
}

async function handleSaveExperience(e) {
  e.preventDefault();
  const bullets = $("#expBullets").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const tech = $("#expTech").value.split(",").map((s) => s.trim()).filter(Boolean);
  const payload = {
    company: $("#expCompany").value,
    role_title: $("#expRole").value,
    location: $("#expLocation").value || null,
    employment_type: $("#expType").value || null,
    start_date: $("#expStart").value,
    end_date: $("#expEnd").value || null,
    is_current: $("#expIsCurrent").checked,
    technologies_used: tech,
    bullet_points: bullets,
  };

  try {
    const editId = $("#expEditId").value;
    if (editId) {
      await API.request(`/profile/experiences/${editId}`, { method: "PUT", body: payload });
    } else {
      await API.request("/profile/experiences", { method: "POST", body: payload });
    }
    closeExperienceModal();
    toast("Experience saved.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteExperience(id) {
  if (!confirm("Delete this experience?")) return;
  try {
    await API.request(`/profile/experiences/${id}`, { method: "DELETE" });
    toast("Experience removed.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// PROJECTS
function renderProjectsList(projects) {
  const container = $("#projectList");
  container.innerHTML = "";
  if (!projects.length) {
    container.innerHTML = `
      <div class="empty-state-card">
        <i data-lucide="folder-git-2"></i>
        <h4>No projects added</h4>
        <p>Showcase open source repositories, client deliverables, or portfolio projects.</p>
        <button class="secondary-btn sm" type="button" onclick="$('#addProjectBtn').click()"><i data-lucide="plus"></i><span>Add Project</span></button>
      </div>`;
    return;
  }
  projects.forEach((proj) => {
    const card = document.createElement("div");
    card.className = "card-item";
    const bulletsHtml = (proj.bullet_points || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("");
    card.innerHTML = `
      <div class="card-item-header">
        <div>
          <h4>${escapeHtml(proj.name)}</h4>
          <p class="text-xs text-muted">${escapeHtml(proj.description || "")}</p>
        </div>
        <div class="card-actions">
          <button class="icon-btn sm" type="button" data-del-proj="${proj.id}"><i data-lucide="trash-2"></i></button>
        </div>
      </div>
      ${proj.technologies_used?.length ? `<p class="text-xs mt-1"><strong>Tech:</strong> ${escapeHtml(proj.technologies_used.join(", "))}</p>` : ""}
      <ul class="clean-list text-sm mt-2">${bulletsHtml}</ul>
    `;
    card.querySelector(`[data-del-proj="${proj.id}"]`).addEventListener("click", () => deleteProject(proj.id));
    container.appendChild(card);
  });
}

function openProjectModal() {
  $("#projectForm").reset();
  $("#projectModal").classList.remove("hidden");
  drawIcons();
}

function closeProjectModal() {
  $("#projectModal").classList.add("hidden");
}

async function handleSaveProject(e) {
  e.preventDefault();
  const tech = $("#projTech").value.split(",").map((s) => s.trim()).filter(Boolean);
  const bullets = $("#projBullets").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const payload = {
    name: $("#projName").value,
    description: $("#projDesc").value || null,
    github_url: $("#projRepo").value || null,
    live_url: $("#projLive").value || null,
    technologies_used: tech,
    bullet_points: bullets,
  };
  try {
    await API.request("/profile/projects", { method: "POST", body: payload });
    closeProjectModal();
    toast("Project saved.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteProject(id) {
  if (!confirm("Delete this project?")) return;
  try {
    await API.request(`/profile/projects/${id}`, { method: "DELETE" });
    toast("Project removed.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// EDUCATION
function renderEducationList(education) {
  const container = $("#educationList");
  container.innerHTML = "";
  if (!education.length) {
    container.innerHTML = `
      <div class="empty-state-card">
        <i data-lucide="graduation-cap"></i>
        <h4>No education added</h4>
        <p>List your university degrees, diplomas, or academic institutions.</p>
        <button class="secondary-btn sm" type="button" onclick="$('#addEducationBtn').click()"><i data-lucide="plus"></i><span>Add Education</span></button>
      </div>`;
    return;
  }
  education.forEach((edu) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `
      <div class="card-item-header">
        <div>
          <h4>${escapeHtml(edu.degree)} <span class="text-muted">in</span> ${escapeHtml(edu.field_of_study || "")}</h4>
          <span class="text-xs text-muted">${escapeHtml(edu.institution)} (${escapeHtml(edu.start_date || "")} — ${escapeHtml(edu.end_date || "")})</span>
        </div>
        <div class="card-actions">
          <button class="icon-btn sm" type="button" data-del-edu="${edu.id}"><i data-lucide="trash-2"></i></button>
        </div>
      </div>
      ${edu.grade ? `<p class="text-xs mt-1"><strong>Grade:</strong> ${escapeHtml(edu.grade)}</p>` : ""}
    `;
    card.querySelector(`[data-del-edu="${edu.id}"]`).addEventListener("click", () => deleteEducation(edu.id));
    container.appendChild(card);
  });
}

function openEducationModal() {
  $("#educationForm").reset();
  $("#educationModal").classList.remove("hidden");
  drawIcons();
}

function closeEducationModal() {
  $("#educationModal").classList.add("hidden");
}

async function handleSaveEducation(e) {
  e.preventDefault();
  const payload = {
    institution: $("#eduInstitution").value,
    degree: $("#eduDegree").value,
    field_of_study: $("#eduField").value || null,
    start_date: $("#eduStart").value || null,
    end_date: $("#eduEnd").value || null,
    grade: $("#eduGpa").value || null,
  };
  try {
    await API.request("/profile/education", { method: "POST", body: payload });
    closeEducationModal();
    toast("Education saved.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteEducation(id) {
  if (!confirm("Delete this education record?")) return;
  try {
    await API.request(`/profile/education/${id}`, { method: "DELETE" });
    toast("Education record removed.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// CERTIFICATIONS
function renderCertificationsList(certs) {
  const container = $("#certList");
  container.innerHTML = "";
  if (!certs.length) {
    container.innerHTML = `
      <div class="empty-state-card">
        <i data-lucide="award"></i>
        <h4>No certifications added</h4>
        <p>Include credentials from AWS, Google Cloud, Microsoft, or specialized institutes.</p>
        <button class="secondary-btn sm" type="button" onclick="$('#addCertBtn').click()"><i data-lucide="plus"></i><span>Add Certification</span></button>
      </div>`;
    return;
  }
  certs.forEach((cert) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `
      <div class="card-item-header">
        <div>
          <h4>${escapeHtml(cert.name)}</h4>
          <span class="text-xs text-muted">${escapeHtml(cert.issuing_organization)} ${cert.issue_date ? "• " + escapeHtml(cert.issue_date) : ""}</span>
        </div>
        <div class="card-actions">
          <button class="icon-btn sm" type="button" data-del-cert="${cert.id}"><i data-lucide="trash-2"></i></button>
        </div>
      </div>
      ${cert.credential_url ? `<a href="${escapeHtml(cert.credential_url)}" target="_blank" class="text-xs text-primary mt-1 inline-block">Verify Credential &nearr;</a>` : ""}
    `;
    card.querySelector(`[data-del-cert="${cert.id}"]`).addEventListener("click", () => deleteCertification(cert.id));
    container.appendChild(card);
  });
}

function openCertModal() {
  $("#certForm").reset();
  $("#certModal").classList.remove("hidden");
  drawIcons();
}

function closeCertModal() {
  $("#certModal").classList.add("hidden");
}

async function handleSaveCert(e) {
  e.preventDefault();
  const payload = {
    name: $("#certName").value,
    issuing_organization: $("#certIssuer").value,
    issue_date: $("#certDate").value || null,
    credential_url: $("#certUrl").value || null,
  };
  try {
    await API.request("/profile/certifications", { method: "POST", body: payload });
    closeCertModal();
    toast("Certification added.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteCertification(id) {
  if (!confirm("Delete this certification?")) return;
  try {
    await API.request(`/profile/certifications/${id}`, { method: "DELETE" });
    toast("Certification removed.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// SKILLS
function renderSkillsList(skills) {
  const container = $("#skillsContainer");
  container.innerHTML = "";
  if (!skills.length) {
    container.innerHTML = `
      <div class="empty-state-card mini">
        <i data-lucide="badge-check"></i>
        <p>No skills added yet. Enter a skill name above and click Add.</p>
      </div>`;
    return;
  }
  skills.forEach((skill) => {
    const chip = document.createElement("span");
    const status = (skill.evidence_status || "UNSUPPORTED").toLowerCase().replace("_", "-");
    const label = (skill.evidence_status || "UNSUPPORTED").replace("_", " ");
    const note = skill.evidence_notes || (skill.evidence_status === "SUPPORTED" ? "Verified by work bullet / project" : "No project or work bullet currently verifies this skill");
    chip.className = `skill-evidence-chip`;
    chip.title = note;
    chip.innerHTML = `
      <span style="font-weight: 500;">${escapeHtml(skill.name)}</span>
      <span class="evidence-status-pill ${status}">${escapeHtml(label)}</span>
      <button type="button" title="Remove" data-del-skill="${skill.id}" style="background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 1.1rem; line-height: 1; padding: 0 2px;">&times;</button>
    `;
    chip.querySelector(`[data-del-skill="${skill.id}"]`).addEventListener("click", () => deleteSkill(skill.id));
    container.appendChild(chip);
  });
  drawIcons();
}

async function handleAddSkill(e) {
  e.preventDefault();
  const input = $("#newSkillName");
  const name = input.value.trim();
  if (!name) return;
  const category = $("#newSkillCategory").value;
  try {
    await API.request("/profile/skills", { method: "POST", body: { name, category } });
    input.value = "";
    toast("Skill added.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteSkill(id) {
  try {
    await API.request(`/profile/skills/${id}`, { method: "DELETE" });
    toast("Skill removed.");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// RESUME IMPORT WITH MANDATORY HUMAN REVIEW
function openImportModal() {
  $("#importModal").classList.remove("hidden");
  $("#importInputSection").classList.remove("hidden");
  $("#importDraftSection").classList.add("hidden");
  $("#commitImportBtn").classList.add("hidden");
  $("#importFileInput").value = "";
  $("#importRawText").value = "";
  drawIcons();
}

function closeImportModal() {
  $("#importModal").classList.add("hidden");
}

async function parseResumeForImport() {
  const fileInput = $("#importFileInput");
  const rawText = $("#importRawText").value.trim();

  if (!fileInput.files.length && !rawText) {
    return toast("Please choose a resume file or paste raw resume text.", "error");
  }

  const btn = $("#parseResumeBtn");
  setButtonLoading(btn, true, "Analyzing & extracting...");
  try {
    let draft;
    if (fileInput.files.length) {
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      draft = await API.request("/profile/import/parse-file", { method: "POST", body: formData });
    } else {
      draft = await API.request("/profile/import/parse-text", { method: "POST", body: { raw_text: rawText } });
    }
    state.importDraft = draft;
    renderImportDraft(draft);
    $("#importInputSection").classList.add("hidden");
    $("#importDraftSection").classList.remove("hidden");
    $("#commitImportBtn").classList.remove("hidden");
    toast("Resume extracted! Please review and verify all details.");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Parse & Extract Profile");
  }
}

function renderImportDraft(draft) {
  $("#draftHeadline").value = draft.headline || "";
  $("#draftSummary").value = draft.summary || "";
  $("#draftPhone").value = draft.phone || "";
  $("#draftLocation").value = draft.location || "";

  // Experiences
  const exps = draft.experiences || [];
  $("#draftExpCount").textContent = exps.length;
  const expList = $("#draftExpList");
  expList.innerHTML = "";
  exps.forEach((exp) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `<strong>${escapeHtml(exp.role_title)}</strong> at ${escapeHtml(exp.company)} (${escapeHtml(exp.start_date || "")} - ${escapeHtml(exp.end_date || "Present")})`;
    expList.appendChild(card);
  });

  // Skills
  const skills = draft.skills || [];
  $("#draftSkillsCount").textContent = skills.length;
  const skillsList = $("#draftSkillsList");
  skillsList.innerHTML = "";
  skills.forEach((sk) => {
    const chip = document.createElement("span");
    chip.className = "skill-chip";
    chip.textContent = typeof sk === "string" ? sk : sk.name;
    skillsList.appendChild(chip);
  });

  // Projects
  const projs = draft.projects || [];
  $("#draftProjCount").textContent = projs.length;
  const projList = $("#draftProjList");
  projList.innerHTML = "";
  projs.forEach((p) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `<strong>${escapeHtml(p.name)}</strong>: ${escapeHtml(p.description || "")}`;
    projList.appendChild(card);
  });

  // Education
  const edus = draft.education || [];
  $("#draftEduCount").textContent = edus.length;
  const eduList = $("#draftEduList");
  eduList.innerHTML = "";
  edus.forEach((e) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `<strong>${escapeHtml(e.degree)}</strong> from ${escapeHtml(e.institution)}`;
    eduList.appendChild(card);
  });
}

async function commitImportDraft() {
  if (!state.importDraft) return;
  const btn = $("#commitImportBtn");
  setButtonLoading(btn, true, "Saving profile...");
  try {
    const payload = {
      ...state.importDraft,
      headline: $("#draftHeadline").value,
      summary: $("#draftSummary").value,
      phone: $("#draftPhone").value,
      location: $("#draftLocation").value,
    };
    await API.request("/profile/import/commit", { method: "POST", body: payload });
    closeImportModal();
    toast("Resume verified and saved to Master Profile!");
    await loadMasterProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Verify & Save to Master Profile");
  }
}

// TAB 2: JOB MATCH & FIT ENGINE
function wireJobFit() {
  $("#runFitAnalysisBtn").addEventListener("click", handleRunFitAnalysis);
  $("#savedJobsSelect").addEventListener("change", (e) => {
    if (e.target.value) selectJob(Number(e.target.value));
  });
  $("#deleteJobBtn").addEventListener("click", handleDeleteJob);
  $("#proceedToTailorBtn").addEventListener("click", () => navigateToTab("tailor"));

  // Evidence Map filter pills
  $$("#evidenceFilterPills button").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$("#evidenceFilterPills button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderEvidenceMap(btn.dataset.filter);
    });
  });
}

async function loadJobs() {
  try {
    const jobs = await API.request("/jobs");
    state.jobs = jobs;
    renderJobsSelect(jobs);
  } catch (error) {
    // Graceful error fallback
  }
}

function renderJobsSelect(jobs) {
  const sel = $("#savedJobsSelect");
  sel.innerHTML = '<option value="">Select a previously saved job</option>';
  jobs.forEach((j) => {
    const opt = document.createElement("option");
    opt.value = j.id;
    opt.textContent = `${j.title} at ${j.company}`;
    if (state.activeJob && state.activeJob.id === j.id) opt.selected = true;
    sel.appendChild(opt);
  });

  // Also populate app job select in tracker
  const appSel = $("#appJobPostingSelect");
  if (appSel) {
    appSel.innerHTML = '<option value="">None (Standalone)</option>';
    jobs.forEach((j) => {
      const opt = document.createElement("option");
      opt.value = j.id;
      opt.textContent = `${j.title} at ${j.company}`;
      appSel.appendChild(opt);
    });
  }
}

async function selectJob(id) {
  const job = state.jobs.find((j) => j.id === id);
  if (!job) return;
  state.activeJob = job;
  $("#targetJobTitle").value = job.title;
  $("#targetCompany").value = job.company;
  $("#targetJobUrl").value = job.job_url || "";
  $("#targetJobDesc").value = job.raw_description || "";
  $("#deleteJobBtn").classList.remove("hidden");
  $("#tailorJobContext").textContent = `Active target job: ${job.title} at ${job.company}`;

  try {
    const fitRes = await API.request(`/jobs/${id}/fit-score`);
    state.lastFitResult = fitRes;
    renderFitResults(fitRes);
  } catch (_) {
    $("#fitScoreEmptyState").classList.remove("hidden");
    $("#fitScoreResults").classList.add("hidden");
    $("#proceedToTailorBtn").classList.add("hidden");
    renderEvidenceMap("all");
  }
  await loadJobVersions(job.id);
}

async function handleRunFitAnalysis() {
  const title = $("#targetJobTitle").value.trim();
  const company = $("#targetCompany").value.trim();
  const desc = $("#targetJobDesc").value.trim();
  if (!title || !company || !desc) {
    return toast("Please fill in job title, company, and complete job description.", "error");
  }

  const btn = $("#runFitAnalysisBtn");
  setButtonLoading(btn, true, "Analyzing ATS Fit...");
  try {
    let job = state.activeJob;
    if (!job || job.title !== title || job.company !== company) {
      job = await API.request("/jobs", {
        method: "POST",
        body: { title, company, raw_description: desc, job_url: $("#targetJobUrl").value.trim() || null },
      });
      state.activeJob = job;
      await loadJobs();
    }

    const fitResult = await API.request(`/jobs/${job.id}/fit-analysis`, { method: "POST" });
    state.lastFitResult = fitResult;
    renderFitResults(fitResult);
    toast("Job Match & Evidence Grounding evaluated successfully!");
    await loadBillingSummary();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Analyze ATS Fit");
  }
}

function renderFitResults(result) {
  if (!result) return;
  $("#fitScoreEmptyState").classList.add("hidden");
  $("#fitScoreResults").classList.remove("hidden");
  $("#proceedToTailorBtn").classList.remove("hidden");

  // Populate Application Readiness Report V2
  const r = result.readiness_report || {};
  const statusBreakdown = r.status_breakdown || {};

  if ($("#readinessVerdictTitle")) {
    $("#readinessVerdictTitle").textContent = r.verdict || "Application Alignment Assessed";
  }
  if ($("#readinessSummaryStatement")) {
    $("#readinessSummaryStatement").textContent = r.summary_statement ||
      "Evaluated against target job requirements using verified Master Profile evidence.";
  }

  // 4 Status Breakdown Counts
  if ($("#countStrongMatches")) {
    $("#countStrongMatches").textContent = statusBreakdown.strong_count ?? (result.matched_skills?.length || 0);
  }
  if ($("#countPartialMatches")) {
    $("#countPartialMatches").textContent = statusBreakdown.partial_count ?? 0;
  }
  if ($("#countMissingReqs")) {
    $("#countMissingReqs").textContent = statusBreakdown.missing_count ?? (result.missing_skills?.length || 0);
  }
  if ($("#countUnclearReqs")) {
    $("#countUnclearReqs").textContent = statusBreakdown.unclear_count ?? 0;
  }

  // 4 Independently Explainable Indicators
  if ($("#indicatorFormat")) {
    const fmtScore = r.format_health?.score ?? result.format_health_score ?? 85;
    $("#indicatorFormat").textContent = `${fmtScore}/100`;
  }
  if ($("#indicatorReqCoverage")) {
    const reqScore = r.requirement_coverage?.score ?? result.keyword_coverage_score ?? 70;
    $("#indicatorReqCoverage").textContent = `${reqScore}%`;
  }
  if ($("#indicatorEvidenceCoverage")) {
    const evScore = r.evidence_coverage?.score ?? result.evidence_match_score ?? 60;
    $("#indicatorEvidenceCoverage").textContent = `${evScore}%`;
  }
  if ($("#indicatorContentQuality")) {
    const qScore = r.content_quality?.score ?? result.content_quality_score ?? 80;
    $("#indicatorContentQuality").textContent = `${qScore}/100`;
  }

  // Backward compatibility elements for automated tests
  const fitScore = result.application_fit_score || 0;
  if ($("#scoreAppFit")) $("#scoreAppFit").textContent = `${fitScore}`;
  const label = $("#scoreAppFitLabel");
  if (label) {
    if (fitScore >= 80) { label.textContent = "High Match (Ready to apply)"; label.style.color = "var(--success)"; }
    else if (fitScore >= 55) { label.textContent = "Moderate Match (Tailoring recommended)"; label.style.color = "var(--warning)"; }
    else { label.textContent = "Low Evidence Match"; label.style.color = "var(--danger)"; }
  }

  if ($("#scoreEvidence")) $("#scoreEvidence").textContent = `${result.evidence_match_score || 0}%`;
  if ($("#scoreKeywords")) $("#scoreKeywords").textContent = `${result.keyword_coverage_score || 0}%`;
  if ($("#scoreFormat")) $("#scoreFormat").textContent = `${result.format_health_score || 0}%`;
  if ($("#scoreQuality")) $("#scoreQuality").textContent = `${result.content_quality_score || 0}%`;

  // Action Hints
  const hintsHost = $("#fitActionHints");
  if (hintsHost) {
    hintsHost.innerHTML = "";
    const hints = result.actionable_guidance || result.actionable_hints || [];
    if (!hints.length) {
      hintsHost.innerHTML = "<li>Profile demonstrates strong alignment with extracted requirements.</li>";
    } else {
      hints.forEach((h) => {
        const li = document.createElement("li");
        li.textContent = h;
        hintsHost.appendChild(li);
      });
    }
  }

  // Skill Gaps Action Panel
  renderSkillGapsActionPanel(result);

  renderEvidenceMap("all");
}

function renderSkillGapsActionPanel(result) {
  const panel = $("#skillGapsActionPanel");
  const list = $("#missingReqActionsList");
  if (!panel || !list) return;

  const r = result.readiness_report || {};
  const missingReqs = r.missing_requirements || [];
  const honestGaps = result.honest_gaps || result.missing_skills || [];

  if (missingReqs.length === 0 && honestGaps.length === 0) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");
  list.innerHTML = "";

  if (missingReqs.length > 0) {
    missingReqs.slice(0, 5).forEach((req) => {
      const card = document.createElement("div");
      card.className = "card-item";
      const reqText = typeof req === "string" ? req : (req.requirement_text || req.requirement || "Requirement");
      const why = req.why_it_matters || "Identified as a critical qualification in target job posting.";
      card.innerHTML = `
        <div class="card-item-header">
          <div>
            <strong>${escapeHtml(reqText)}</strong>
            <p class="text-xs text-muted mt-1">${escapeHtml(why)}</p>
          </div>
          <span class="evidence-status-pill missing">MISSING EVIDENCE</span>
        </div>
        <div class="button-row mt-2">
          <button class="secondary-btn sm" type="button" data-gap-blueprint="${escapeHtml(reqText)}">
            <i data-lucide="compass"></i><span>Draft Mini-Project Blueprint</span>
          </button>
          <button class="ghost-btn sm" type="button" data-gap-exp="true">
            <i data-lucide="plus"></i><span>Add Existing Proof</span>
          </button>
        </div>
      `;
      card.querySelector("[data-gap-blueprint]").addEventListener("click", () => openLearningGapModal(reqText));
      card.querySelector("[data-gap-exp]").addEventListener("click", () => {
        navigateToTab("profile");
        openExperienceModal();
      });
      list.appendChild(card);
    });
  } else {
    honestGaps.slice(0, 5).forEach((gap) => {
      const card = document.createElement("div");
      card.className = "card-item";
      card.innerHTML = `
        <div class="card-item-header">
          <div>
            <strong>${escapeHtml(gap)}</strong>
            <p class="text-xs text-muted mt-1">Lacked verified evidence in profile — omitted from auto-tailoring to prevent fabrication.</p>
          </div>
          <span class="evidence-status-pill missing">GAP</span>
        </div>
        <div class="button-row mt-2">
          <button class="secondary-btn sm" type="button" data-gap-blueprint="${escapeHtml(gap)}">
            <i data-lucide="compass"></i><span>Draft Mini-Project Blueprint</span>
          </button>
        </div>
      `;
      card.querySelector("[data-gap-blueprint]").addEventListener("click", () => openLearningGapModal(gap));
      list.appendChild(card);
    });
  }
  drawIcons();
}


function renderEvidenceMap(filter = "all") {
  const container = $("#evidenceMapContainer");
  container.innerHTML = "";
  const reqs = state.lastFitResult?.requirements || [];

  const filtered = filter === "all" ? reqs : reqs.filter((r) => r.match_status?.toUpperCase() === filter.toUpperCase());
  if (!filtered.length) {
    container.innerHTML = `<div class="empty-state-card mini"><i data-lucide="shield-check"></i><p>No requirements match filter "${filter}".</p></div>`;
    drawIcons();
    return;
  }

  filtered.forEach((r) => {
    const card = document.createElement("div");
    card.className = "card-item";
    const statusClass = r.match_status === "STRONG" ? "badge-musthave" : r.match_status === "PARTIAL" ? "badge-sub" : "badge-missing";
    card.innerHTML = `
      <div class="card-item-header">
        <strong>${escapeHtml(r.requirement_text)}</strong>
        <span class="${statusClass}">${escapeHtml(r.match_status || "UNCHECKED")}</span>
      </div>
      <p class="text-xs text-muted mt-1"><strong>Category:</strong> ${escapeHtml(r.category || "General")} | <strong>Source:</strong> ${escapeHtml(r.evidence_source || "None")}</p>
      ${r.evidence_snippet ? `<p class="text-xs mt-1"><em>Evidence: "${escapeHtml(r.evidence_snippet)}"</em></p>` : ""}
    `;
    container.appendChild(card);
  });
}

async function handleDeleteJob() {
  if (!state.activeJob || !confirm(`Delete job "${state.activeJob.title}"?`)) return;
  try {
    await API.request(`/jobs/${state.activeJob.id}`, { method: "DELETE" });
    state.activeJob = null;
    state.lastFitResult = null;
    $("#targetJobTitle").value = "";
    $("#targetCompany").value = "";
    $("#targetJobUrl").value = "";
    $("#targetJobDesc").value = "";
    $("#deleteJobBtn").classList.add("hidden");
    $("#fitScoreResults").classList.add("hidden");
    $("#fitScoreEmptyState").classList.remove("hidden");
    toast("Job deleted.");
    await loadJobs();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// // TAB 3: TAILORING STUDIO
function wireTailoringStudio() {
  $("#generateTailoringBtn").addEventListener("click", handleGenerateTailoring);
  $("#acceptAllDiffsBtn").addEventListener("click", () => toggleAllDiffs(true));
  $("#rejectAllDiffsBtn").addEventListener("click", () => toggleAllDiffs(false));
  $("#commitVersionBtn").addEventListener("click", handleCommitVersion);
  $("#refreshVersionsListBtn").addEventListener("click", () => {
    if (state.activeJob) loadJobVersions(state.activeJob.id);
  });

  $("#downloadPdfBtn").addEventListener("click", () => handleExportWithPreCheck("pdf"));
  $("#downloadDocxBtn").addEventListener("click", () => handleExportWithPreCheck("docx"));
}

async function handleGenerateTailoring() {
  if (!state.activeJob) {
    return toast("Please select a target job posting from Job Match & Fit first.", "error");
  }
  const btn = $("#generateTailoringBtn");
  setButtonLoading(btn, true, "Generating proposal...");
  try {
    const proposal = await API.request(`/jobs/${state.activeJob.id}/tailor-proposal`, { method: "POST" });
    state.lastTailoringProposal = proposal;
    renderTailoringProposal(proposal);
    toast("Tailoring proposal generated with zero fabrication guarantee.");
    await loadBillingSummary();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Generate Tailoring Proposal");
  }
}

function renderTailoringProposal(proposal) {
  if (!proposal) return;

  // Honest Gaps Banner (Zero hallucination policy)
  const gaps = proposal.unmatched_requirements_honest_gaps || [];
  const gapsBanner = $("#honestGapsBanner");
  if (gaps.length > 0) {
    gapsBanner.classList.remove("hidden");
    const list = $("#honestGapsList");
    list.innerHTML = "";
    gaps.forEach((g) => {
      const pill = document.createElement("span");
      pill.className = "gap-pill";
      pill.textContent = g;
      list.appendChild(pill);
    });
  } else {
    gapsBanner.classList.add("hidden");
  }

  // Populate diff list
  const bullets = proposal.tailored_bullets || [];
  state.tailoredBulletsState = bullets.map((b, idx) => ({
    id: idx,
    exp_id: b.experience_id,
    original: b.original_bullet,
    tailored: b.tailored_bullet,
    rationale: b.rationale,
    accepted: true,
  }));

  renderDiffCards();
  $("#tailoringDiffContainer").classList.remove("hidden");
}

function renderDiffCards() {
  const container = $("#diffItemsList");
  container.innerHTML = "";

  state.tailoredBulletsState.forEach((item) => {
    const card = document.createElement("div");
    card.className = `diff-card ${item.accepted ? "accepted" : "rejected"}`;
    card.innerHTML = `
      <div class="diff-header">
        <span class="diff-status-badge ${item.accepted ? "badge-musthave" : "badge-missing"}">
          ${item.accepted ? "ACCEPTED FOR SNAPSHOT" : "REJECTED (Original Bullet Kept)"}
        </span>
        <div class="card-actions">
          <button class="secondary-btn sm" type="button" data-accept-diff="${item.id}"><i data-lucide="check"></i> Accept Proposal</button>
          <button class="ghost-btn sm" type="button" data-reject-diff="${item.id}"><i data-lucide="x"></i> Keep Original</button>
        </div>
      </div>
      <div class="diff-columns mt-2">
        <div class="diff-col original">
          <span class="text-xs text-muted" style="font-weight:600;">Original Master Profile Bullet:</span>
          <p class="text-sm mt-1">${escapeHtml(item.original)}</p>
        </div>
        <div class="diff-col tailored">
          <span class="text-xs text-muted" style="font-weight:600;">Proposed Evidence-Grounded Reframe:</span>
          <p class="text-sm mt-1">${escapeHtml(item.tailored)}</p>
        </div>
      </div>
      <div class="dimension-why mt-2">
        <strong>Recommendation Context:</strong> ${escapeHtml(item.rationale || "Reframed with strong, level-appropriate action verbs and metrics without fabricating unverified claims.")}
        <span class="text-xs text-muted" style="display:block; margin-top: 4px;"><em>Scope: Modifies this version snapshot only. Your Master Profile remains immutable.</em></span>
      </div>
    `;

    card.querySelector(`[data-accept-diff="${item.id}"]`).addEventListener("click", () => {
      item.accepted = true;
      renderDiffCards();
    });
    card.querySelector(`[data-reject-diff="${item.id}"]`).addEventListener("click", () => {
      item.accepted = false;
      renderDiffCards();
    });

    container.appendChild(card);
  });
  drawIcons();
}


function toggleAllDiffs(accept) {
  state.tailoredBulletsState.forEach((item) => { item.accepted = accept; });
  renderDiffCards();
}

async function handleCommitVersion() {
  if (!state.activeJob || !state.lastTailoringProposal) {
    return toast("Generate a tailoring proposal first.", "error");
  }

  const template = $("#templateSelector").value;
  const changelog = $("#versionChangelog").value || "Tailored ATS snapshot";
  const approvedBullets = state.tailoredBulletsState.map((b) => ({
    experience_id: b.exp_id,
    bullet: b.accepted ? b.tailored : b.original,
  }));

  const btn = $("#commitVersionBtn");
  setButtonLoading(btn, true, "Saving version...");
  try {
    const payload = {
      template_name: template,
      changelog_note: changelog,
      approved_bullets: approvedBullets,
    };
    const version = await API.request(`/jobs/${state.activeJob.id}/versions`, { method: "POST", body: payload });
    toast("Immutable version snapshot created successfully!");
    $("#tailoringDiffContainer").classList.add("hidden");
    await loadJobVersions(state.activeJob.id);
    previewVersion(version);
    await loadBillingSummary();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Save Version Snapshot");
  }
}

async function loadJobVersions(jobId) {
  try {
    const versions = await API.request(`/jobs/${jobId}/versions`);
    state.versions = versions;
    renderVersionsList(versions);
  } catch (_) {}
}

function renderVersionsList(versions) {
  const container = $("#jobVersionsList");
  container.innerHTML = "";
  if (!versions.length) {
    container.innerHTML = `
      <div class="empty-state-card">
        <i data-lucide="history"></i>
        <h4>No version snapshots saved</h4>
        <p>Generate a tailoring proposal and save a version snapshot to lock down an immutable copy for export.</p>
      </div>`;
    drawIcons();
    return;
  }

  versions.forEach((ver) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `
      <div class="card-item-header">
        <div>
          <h4>Version #${ver.version_number} — <span class="badge-sub">${escapeHtml(ver.template_name)}</span></h4>
          <span class="text-xs text-muted">ATS Score: ${ver.ats_score}% • Created ${escapeHtml(ver.created_at ? ver.created_at.slice(0, 10) : "")}</span>
        </div>
        <div class="flex-row gap-2">
          <button class="secondary-btn sm" type="button" data-preview-ver="${ver.id}">Preview</button>
          <button class="primary-btn sm" type="button" data-pack-ver="${ver.id}"><i data-lucide="package"></i><span>Pack</span></button>
        </div>
      </div>
      ${ver.changelog_note ? `<p class="text-xs mt-1 text-muted">${escapeHtml(ver.changelog_note)}</p>` : ""}
    `;
    card.querySelector(`[data-preview-ver="${ver.id}"]`).addEventListener("click", () => previewVersion(ver));
    card.querySelector(`[data-pack-ver="${ver.id}"]`).addEventListener("click", () => openApplicationPack(ver.id));
    container.appendChild(card);
  });
  drawIcons();
}

async function previewVersion(ver) {
  state.activeVersion = ver;
  $("#downloadPdfBtn").classList.remove("hidden");
  $("#downloadDocxBtn").classList.remove("hidden");

  const sheet = $("#resumePreviewSheet");
  const c = ver.content_json || {};

  const expHtml = (c.experiences || []).map((exp) => `
    <div class="mb-3">
      <div class="flex-row justify-between">
        <strong>${escapeHtml(exp.role_title)}</strong> — <span>${escapeHtml(exp.company)}</span>
      </div>
      <span class="text-xs text-muted">${escapeHtml(exp.start_date || "")} - ${exp.is_current ? "Present" : escapeHtml(exp.end_date || "")}</span>
      <ul class="clean-list text-xs mt-2">${(exp.bullet_points || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>
    </div>
  `).join("");

  const skillsHtml = (c.skills || []).map((sk) => `<span class="skill-chip">${escapeHtml(typeof sk === "string" ? sk : sk.name)}</span>`).join(" ");

  sheet.innerHTML = `
    <div class="preview-content">
      <div class="text-center mb-4">
        <h2>${escapeHtml(c.candidate_name || state.user?.full_name || "Candidate Resume")}</h2>
        <p class="text-sm">${escapeHtml(c.headline || "")}</p>
        <p class="text-xs text-muted">${escapeHtml(c.contact_info?.email || state.user?.email || "")} | ${escapeHtml(c.contact_info?.phone || "")} | ${escapeHtml(c.contact_info?.location || "")}</p>
      </div>

      <hr class="mb-3" style="border: 0; border-top: 1px solid var(--border);" />

      <h4 class="mb-2">EXPERIENCE</h4>
      ${expHtml || "<p class='text-xs text-muted'>No experience listed.</p>"}

      <h4 class="mt-4 mb-2">TECHNICAL SKILLS</h4>
      <div class="skills-chip-grid mb-3">${skillsHtml || "<p class='text-xs text-muted'>No skills listed.</p>"}</div>
    </div>
  `;
}

async function exportActiveVersion(format) {
  if (!state.activeJob || !state.activeVersion) {
    return toast("Select a version snapshot first.", "error");
  }
  try {
    toast(`Preparing ${format.toUpperCase()} export...`);
    const blob = await API.request(
      `/jobs/${state.activeJob.id}/versions/${state.activeVersion.id}/export?format=${format}&template=${state.activeVersion.template_name}`,
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${state.user?.full_name || "Resume"}_${state.activeVersion.template_name}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
    toast(`${format.toUpperCase()} downloaded successfully.`);
    await loadBillingSummary();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// TAB 4: APPLICATIONS TRACKER
function wireApplications() {
  $("#applicationForm").addEventListener("submit", handleSaveApplication);
  $("#refreshApplicationsBtn").addEventListener("click", loadApplications);
}

async function loadApplications() {
  try {
    const apps = await API.request("/applications");
    state.applications = apps;
    renderApplicationsList(apps);
  } catch (error) {
    // Graceful error handling
  }
}

function renderApplicationsList(apps) {
  const container = $("#applicationList");
  container.innerHTML = "";
  if (!apps.length) {
    container.innerHTML = `
      <div class="empty-state-card">
        <i data-lucide="briefcase"></i>
        <h4>No tracked applications</h4>
        <p>Track your job submissions, interview stages, and offers in one organized dashboard.</p>
      </div>`;
    drawIcons();
    return;
  }

  apps.forEach((app) => {
    const card = document.createElement("div");
    card.className = "card-item";
    card.innerHTML = `
      <div class="card-item-header">
        <div>
          <h4>${escapeHtml(app.job_title)} <span class="text-muted">at</span> ${escapeHtml(app.company)}</h4>
          <span class="badge-musthave">${escapeHtml(app.status)}</span>
          ${app.job_url ? `<a href="${escapeHtml(app.job_url)}" target="_blank" class="text-xs text-primary ml-2">Job Link &nearr;</a>` : ""}
        </div>
        <div class="card-actions">
          <select class="text-xs" data-status-app="${app.id}">
            <option value="SAVED" ${app.status === "SAVED" ? "selected" : ""}>SAVED</option>
            <option value="APPLIED" ${app.status === "APPLIED" ? "selected" : ""}>APPLIED</option>
            <option value="INTERVIEW" ${app.status === "INTERVIEW" ? "selected" : ""}>INTERVIEW</option>
            <option value="OFFER" ${app.status === "OFFER" ? "selected" : ""}>OFFER</option>
            <option value="REJECTED" ${app.status === "REJECTED" ? "selected" : ""}>REJECTED</option>
          </select>
          <button class="icon-btn sm" type="button" data-del-app="${app.id}"><i data-lucide="trash-2"></i></button>
        </div>
      </div>
      ${app.notes ? `<p class="text-xs text-muted mt-1">${escapeHtml(app.notes)}</p>` : ""}
    `;
    card.querySelector(`[data-status-app="${app.id}"]`).addEventListener("change", (e) => updateAppStatus(app.id, e.target.value));
    card.querySelector(`[data-del-app="${app.id}"]`).addEventListener("click", () => deleteApplication(app.id));
    container.appendChild(card);
  });
  drawIcons();
}

async function handleSaveApplication(e) {
  e.preventDefault();
  const payload = {
    company: $("#appCompany").value,
    job_title: $("#appJobTitle").value,
    job_url: $("#appJobUrl").value || null,
    status: $("#appStatus").value,
    notes: $("#appNotes").value || null,
    job_posting_id: $("#appJobPostingSelect").value ? Number($("#appJobPostingSelect").value) : null,
  };
  try {
    await API.request("/applications", { method: "POST", body: payload });
    $("#applicationForm").reset();
    toast("Application saved.");
    await loadApplications();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function updateAppStatus(id, status) {
  try {
    await API.request(`/applications/${id}`, { method: "PATCH", body: { status } });
    toast(`Status updated to ${status}.`);
    await loadApplications();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteApplication(id) {
  if (!confirm("Delete this tracked application?")) return;
  try {
    await API.request(`/applications/${id}`, { method: "DELETE" });
    toast("Application deleted.");
    await loadApplications();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// TAB 5: BILLING, PRICING & PAYMENT ORCHESTRATION
function wireBilling() {
  $("#upgradeBtn").addEventListener("click", () => navigateToTab("billing"));

  // Currency Selector
  $("#currencySelector").addEventListener("change", (e) => {
    state.selectedCurrency = e.target.value;
    updateCurrencyDisplay();
  });

  // ₹1 One-Time Test Export (Rule 11 & Rule 16)
  $("#checkoutSingleExportBtn").addEventListener("click", handleSingleExportTestPayment);

  // Pro Upgrade buttons
  $("#upgradeProBtn").addEventListener("click", () => openRecurringConsentModal("PRO_MONTHLY"));
  $("#upgradeAnnualBtn").addEventListener("click", () => openRecurringConsentModal("PRO_ANNUAL"));

  // Recurring Consent Modal interactions
  $("#closeConsentModalBtn").addEventListener("click", closeRecurringConsentModal);
  $("#cancelConsentBtn").addEventListener("click", closeRecurringConsentModal);
  $("#consentAcknowledgeCheck").addEventListener("change", (e) => {
    $("#confirmConsentBtn").disabled = !e.target.checked;
  });
  $("#confirmConsentBtn").addEventListener("click", () => {
    const planKey = state.pendingPlanKey;
    closeRecurringConsentModal();
    if (planKey) handleUpgrade(planKey);
  });

  // Cancel Subscription button
  $("#cancelSubscriptionBtn").addEventListener("click", handleCancelSubscription);
  $("#refreshPaymentHistoryBtn").addEventListener("click", loadPaymentHistory);
}

async function loadPricingData() {
  try {
    const data = await API.request("/payments/pricing");
    state.pricingData = data;
    if (data.test_upi_id) {
      $("#displayTestUpiId").textContent = data.test_upi_id;
    }
    updateCurrencyDisplay();
  } catch (_) {}
}

function updateCurrencyDisplay() {
  const curr = state.selectedCurrency || "INR";
  const p = state.pricingData?.currencies?.[curr] || { symbol: "₹", single: 1, pro_monthly: 79, pro_annual: 699, pack_10: 29, pack_20: 49, pack_50: 99 };

  $("#priceSingleExport").innerHTML = `${p.symbol}${p.single} <span>one-time</span>`;
  $$(".single-price-inline").forEach((el) => { el.textContent = `${p.symbol}${p.single}`; });
  $("#priceProMonthly").innerHTML = `${p.symbol}${p.pro_monthly} <span>/ month</span>`;
  $("#priceProAnnual").innerHTML = `${p.symbol}${p.pro_annual} <span>/ year</span>`;
  $("#pricePack10").textContent = `${p.symbol}${p.pack_10}`;
  $("#pricePack20").textContent = `${p.symbol}${p.pack_20}`;
  $("#pricePack50").textContent = `${p.symbol}${p.pack_50}`;
}

async function openRecurringConsentModal(planKey) {
  state.pendingPlanKey = planKey;
  const curr = state.selectedCurrency || "INR";
  try {
    const info = await API.request(`/payments/consent-info?plan=${planKey}&currency=${curr}`);
    $("#consentPlanName").textContent = info.display_name;
    $("#consentAmount").textContent = `${info.currency_symbol}${info.amount} / ${info.frequency || "period"}`;
    $("#consentFrequency").textContent = capitalize(info.billing_frequency || info.frequency);
    $("#consentRenewalDate").textContent = `${info.next_renewal_days} days from today`;
    $("#consentNoticeText").textContent = info.regulatory_note || info.mandate_notice;
  } catch (_) {
    $("#consentPlanName").textContent = planKey === "PRO_ANNUAL" ? "Annual Power Plan" : "Pro Monthly Plan";
  }

  $("#consentAcknowledgeCheck").checked = false;
  $("#confirmConsentBtn").disabled = true;
  $("#recurringConsentModal").classList.remove("hidden");
  drawIcons();
}

function closeRecurringConsentModal() {
  $("#recurringConsentModal").classList.add("hidden");
  state.pendingPlanKey = null;
}

// ₹1 Single Export Test Payment (Rule 11 & Rule 16)
async function handleSingleExportTestPayment() {
  const btn = $("#checkoutSingleExportBtn");
  setButtonLoading(btn, true, "Creating test order...");
  try {
    const order = await API.request("/payments/create-order", {
      method: "POST",
      body: { plan: "SINGLE_EXPORT", currency: state.selectedCurrency },
    });

    if (order.is_test || order.provider === "mock" || order.payment_mode === "test") {
      // Simulate direct instant test verification
      toast("Test mode active: simulating instant payment capture...");
      const verifyRes = await API.request("/payments/verify", {
        method: "POST",
        body: {
          order_id: order.order_id,
          payment_id: `pay_test_${order.order_id}`,
          plan: "SINGLE_EXPORT",
        },
      });
      toast(verifyRes.message || "Test payment verified! 1 resume export credit added.");
      await loadBillingSummary();
      await loadPaymentHistory();
      renderDashboard();
      return;
    }

    // Live Razorpay Checkout for ₹1
    if (!window.Razorpay) {
      return toast("Payment gateway is initializing. Please try again.", "error");
    }
    const rzp = new window.Razorpay({
      key: order.razorpay_key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.order_id,
      name: "SmartResume.ai",
      description: "Single Export Test Payment (Non-recurring)",
      handler: async (response) => {
        try {
          await API.request("/payments/verify", {
            method: "POST",
            body: {
              order_id: response.razorpay_order_id,
              payment_id: response.razorpay_payment_id,
              signature: response.razorpay_signature,
              plan: "SINGLE_EXPORT",
            },
          });
          toast("Payment verified! 1 resume export credit added.");
          await loadBillingSummary();
          await loadPaymentHistory();
          renderDashboard();
        } catch (err) {
          toast(err.message, "error");
        }
      },
    });
    rzp.open();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Test Checkout");
  }
}

async function handleUpgrade(planKey) {
  try {
    const order = await API.request("/payments/create-order", {
      method: "POST",
      body: { plan: planKey, currency: state.selectedCurrency },
    });

    if (order.provider === "mock" || order.is_test) {
      state.user = await API.request("/users/profile");
      renderUserBar();
      toast("Plan upgraded successfully in development mode!");
      await loadBillingSummary();
      await loadPaymentHistory();
      renderDashboard();
      return;
    }

    if (!window.Razorpay) {
      return toast("Razorpay checkout is unavailable.", "error");
    }
    const rzp = new window.Razorpay({
      key: order.razorpay_key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.order_id,
      name: "SmartResume.ai",
      description: planKey === "PRO_ANNUAL" ? "Annual Power Plan" : "Pro Monthly Plan",
      handler: async (response) => {
        try {
          await API.request("/payments/verify", {
            method: "POST",
            body: {
              order_id: response.razorpay_order_id,
              payment_id: response.razorpay_payment_id,
              signature: response.razorpay_signature,
              plan: planKey,
            },
          });
          toast("Subscription activated successfully!");
          state.user = await API.request("/users/profile");
          renderUserBar();
          await loadBillingSummary();
          await loadPaymentHistory();
          renderDashboard();
        } catch (err) {
          toast(err.message, "error");
        }
      },
    });
    rzp.open();
  } catch (error) {
    toast(error.message, "error");
  }
}

function handleBoosterPack(packKey) {
  toast(`Purchasing ${packKey.toUpperCase()} via gateway...`);
  handleUpgrade(packKey.toUpperCase());
}

async function loadBillingSummary() {
  try {
    const data = await API.request("/payments/billing-summary");
    state.quotas = data;
    renderBillingSummary(data);
  } catch (_) {}
}

function renderBillingSummary(data) {
  if (!data) return;
  const q = data.quotas || {};
  const fits = q.fit_analyses || { used: 0, limit: 2 };
  const tailors = q.tailored_versions || { used: 0, limit: 2 };
  const exports_ = q.exports || { used: 0, limit: 2 };

  // Topbar quick quota badge
  $("#quickFitsUsage").textContent = `${fits.used}/${fits.limit}`;
  $("#quickTailorUsage").textContent = `${tailors.used}/${tailors.limit}`;
  $("#quickExportUsage").textContent = `${exports_.used}/${exports_.limit}`;

  // Billing tab cards
  $("#quotaFitsText").textContent = `${fits.used} / ${fits.limit}`;
  $("#quotaFitsBar").style.width = `${Math.min(100, Math.round((fits.used / (fits.limit || 1)) * 100))}%`;

  $("#quotaTailorsText").textContent = `${tailors.used} / ${tailors.limit}`;
  $("#quotaTailorsBar").style.width = `${Math.min(100, Math.round((tailors.used / (tailors.limit || 1)) * 100))}%`;

  $("#quotaExportsText").textContent = `${exports_.used} / ${exports_.limit}`;
  $("#quotaExportsBar").style.width = `${Math.min(100, Math.round((exports_.used / (exports_.limit || 1)) * 100))}%`;

  $("#quotaResetDate").textContent = data.quota_resets_at || "1st of next month";
}

async function loadPaymentHistory() {
  try {
    const history = await API.request("/payments/history");
    state.paymentHistory = history;
    renderPaymentHistory(history);
  } catch (_) {}
}

function renderPaymentHistory(history) {
  const tbody = $("#paymentHistoryTbody");
  tbody.innerHTML = "";
  if (!history || !history.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">No payment events recorded.</td></tr>`;
    return;
  }
  history.forEach((evt) => {
    const tr = document.createElement("tr");
    const dt = evt.created_at ? evt.created_at.slice(0, 10) : "--";
    const details = evt.details || {};
    const plan = details.plan || evt.event_type || "Payment";
    const amt = details.amount ? `${details.amount / 100} ${details.currency || "INR"}` : "--";
    tr.innerHTML = `
      <td>${escapeHtml(dt)}</td>
      <td><strong>${escapeHtml(plan)}</strong></td>
      <td>${escapeHtml(amt)}</td>
      <td><code class="text-xs">${escapeHtml(evt.event_id || "--")}</code></td>
      <td><span class="badge-musthave">COMPLETED</span></td>
    `;
    tbody.appendChild(tr);
  });
}

async function handleCancelSubscription() {
  if (!confirm("Cancel recurring subscription? You will remain on the Free plan without automatic renewals.")) return;
  try {
    await API.request("/payments/cancel", { method: "POST" });
    toast("Subscription cancelled immediately.");
    state.user = await API.request("/users/profile");
    renderUserBar();
    await loadBillingSummary();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

// TAB 6: SETTINGS
function wireSettings() {
  $("#profileForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      state.user = await API.request("/users/profile", {
        method: "PATCH",
        body: { full_name: $("#profileName").value },
      });
      renderUserBar();
      toast("Profile updated successfully.");
      renderDashboard();
    } catch (error) {
      toast(error.message, "error");
    }
  });

  $("#passwordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await API.request("/users/change-password", {
        method: "POST",
        body: {
          current_password: $("#currentPassword").value,
          new_password: $("#newPassword").value,
        },
      });
      $("#passwordForm").reset();
      toast("Password updated successfully.");
    } catch (error) {
      toast(error.message, "error");
    }
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// PRODUCT INTELLIGENCE V2 MODALS & WORKFLOWS
let pendingExportAction = null;

function wireIntelligenceModals() {
  // Health Report Modal close
  $("#closeHealthModalBtn")?.addEventListener("click", () => $("#healthModal")?.classList.add("hidden"));
  $("#dismissHealthModalBtn")?.addEventListener("click", () => $("#healthModal")?.classList.add("hidden"));

  // Relevance Modal close
  $("#closeRelevanceModalBtn")?.addEventListener("click", () => $("#relevanceModal")?.classList.add("hidden"));
  $("#dismissRelevanceModalBtn")?.addEventListener("click", () => $("#relevanceModal")?.classList.add("hidden"));

  // Learning Gap Modal close & copy
  $("#closeLearningGapModalBtn")?.addEventListener("click", () => $("#learningGapModal")?.classList.add("hidden"));
  $("#dismissLearningGapModalBtn")?.addEventListener("click", () => $("#learningGapModal")?.classList.add("hidden"));
  $("#copyBlueprintBtn")?.addEventListener("click", () => {
    const text = `${$("#blueprintProjectTitle")?.textContent || ""}\n${$("#blueprintEstHours")?.textContent || ""}\n\nOverview:\n${$("#blueprintOverview")?.textContent || ""}\n\nDeliverables:\n${$("#blueprintDeliverables")?.textContent || ""}\n\nProposed Bullet:\n${$("#blueprintBullet")?.textContent || ""}`;
    navigator.clipboard?.writeText(text);
    toast("Blueprint copied to clipboard.");
  });

  // Pre-Export Modal
  $("#closePreExportModalBtn")?.addEventListener("click", () => $("#preExportModal")?.classList.add("hidden"));
  $("#preExportEditBtn")?.addEventListener("click", () => $("#preExportModal")?.classList.add("hidden"));
  $("#preExportProceedBtn")?.addEventListener("click", () => {
    if (pendingExportAction) {
      const action = pendingExportAction;
      pendingExportAction = null;
      action();
    }
  });

  // Onboarding Modal
  wireOnboardingModal();

  // Expose to window for inline HTML onclick handlers
  window.openHealthReportModal = openHealthReportModal;
  window.openRelevanceModal = openRelevanceModal;
  window.openLearningGapModal = openLearningGapModal;
}

async function openHealthReportModal() {
  const modal = $("#healthModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  const list = $("#healthDimensionsList");
  list.innerHTML = `<div class="empty-state-card mini"><i data-lucide="loader"></i><p>Evaluating 10 health dimensions...</p></div>`;
  drawIcons();

  try {
    const health = await API.request("/profile/health-report");
    if ($("#healthOverallScore")) $("#healthOverallScore").textContent = `${health.overall_score || 0}/100`;
    if ($("#healthLevelBadge")) $("#healthLevelBadge").textContent = `Career Level: ${(health.career_level || "DEVELOPING_PROFESSIONAL").replace(/_/g, " ")}`;
    if ($("#healthOverallSummary")) {
      $("#healthOverallSummary").textContent = health.overall_summary ||
        "Evaluated across 10 deterministic dimensions. Every score is explainable with concrete evidence.";
    }

    list.innerHTML = "";
    const dims = health.dimensions || [];
    dims.forEach((d) => {
      const card = document.createElement("div");
      card.className = "dimension-card";
      const pct = Math.min(100, Math.max(0, d.score || 0));
      const statusClass = pct >= 80 ? "supported" : pct >= 50 ? "partial" : "missing";
      card.innerHTML = `
        <div class="dimension-header">
          <div class="dimension-title">
            <i data-lucide="check-circle-2"></i>
            <span>${escapeHtml(d.name)}</span>
          </div>
          <div>
            <strong>${pct}/100</strong>
            <span class="evidence-status-pill ${statusClass} ml-2">${escapeHtml(d.status || (pct >= 80 ? "EXCELLENT" : pct >= 50 ? "GOOD" : "NEEDS IMPROVEMENT"))}</span>
          </div>
        </div>
        <div class="dimension-bar-track">
          <div class="dimension-bar-fill" style="width: ${pct}%;"></div>
        </div>
        <div class="dimension-why">
          <strong>WHY:</strong> ${escapeHtml(d.explanation || "Evaluated against standard career benchmarks.")}
        </div>
        ${d.recommendation ? `<p class="text-xs text-muted mt-1"><strong>Action:</strong> ${escapeHtml(d.recommendation)}</p>` : ""}
      `;
      list.appendChild(card);
    });
    drawIcons();
  } catch (err) {
    list.innerHTML = `<div class="alert-info"><p>Failed to load health report: ${escapeHtml(err.message)}</p></div>`;
  }
}

async function openRelevanceModal() {
  const modal = $("#relevanceModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  const list = $("#relevanceItemsList");
  list.innerHTML = `<div class="empty-state-card mini"><i data-lucide="loader"></i><p>Scanning profile for low-value content...</p></div>`;
  drawIcons();

  try {
    const domain = $("#profDomain")?.value || state.profile?.target_domain || "Software Engineering";
    const report = await API.request(`/profile/relevance-check?domain=${encodeURIComponent(domain)}`);
    if ($("#relevanceDomainContext")) {
      $("#relevanceDomainContext").innerHTML = `Target Domain Context: <strong>${escapeHtml(report.domain || domain)}</strong>`;
    }

    list.innerHTML = "";
    const items = report.flagged_items || [];
    if (!items.length) {
      list.innerHTML = `
        <div class="empty-state-card mini">
          <i data-lucide="check-check"></i>
          <h4>Clean & High-Relevance Content</h4>
          <p>No low-value or distracting items found for your target domain. High signal-to-noise ratio maintained!</p>
        </div>`;
      drawIcons();
      return;
    }

    items.forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "relevance-item-card";
      card.innerHTML = `
        <div class="relevance-item-header">
          <div>
            <strong>${escapeHtml(item.item_name || item.name || "Item")}</strong>
            <span class="badge-sub ml-2">${escapeHtml(item.category || "General")}</span>
          </div>
          <span class="evidence-status-pill ${item.recommendation === "REMOVE" ? "missing" : "partial"}">
            ${escapeHtml(item.recommendation || "REVIEW")}
          </span>
        </div>
        <div class="dimension-why">
          <strong>WHY:</strong> ${escapeHtml(item.reason || "May dilute technical qualifications for this domain.")}
        </div>
        <div class="button-row mt-1">
          <button class="secondary-btn sm" type="button" data-rel-action="keep">Keep</button>
          <button class="danger-btn sm" type="button" data-rel-action="remove">Remove</button>
          <button class="ghost-btn sm" type="button" data-rel-action="optional">Mark Optional</button>
        </div>
      `;

      card.querySelector('[data-rel-action="keep"]').addEventListener("click", () => {
        card.style.opacity = "0.5";
        toast("Kept item in profile.");
      });
      card.querySelector('[data-rel-action="remove"]').addEventListener("click", async () => {
        if (item.skill_id) {
          await deleteSkill(item.skill_id);
          card.remove();
        } else {
          card.remove();
          toast("Item removed from review.");
        }
      });
      card.querySelector('[data-rel-action="optional"]').addEventListener("click", () => {
        card.style.opacity = "0.5";
        toast("Marked as optional.");
      });

      list.appendChild(card);
    });
    drawIcons();
  } catch (err) {
    list.innerHTML = `<div class="alert-info"><p>Failed to run relevance check: ${escapeHtml(err.message)}</p></div>`;
  }
}

async function openLearningGapModal(skillOrReq) {
  const modal = $("#learningGapModal");
  if (!modal) return;
  modal.classList.remove("hidden");

  $("#blueprintProjectTitle").textContent = `Bridge Gap: ${skillOrReq}`;
  $("#blueprintEstHours").textContent = "Est: 8–16 hours";
  $("#blueprintOverview").textContent = `Hands-on mini-project to build verifiable evidence for "${skillOrReq}" before adding it to your resume.`;
  $("#blueprintDeliverables").innerHTML = "<li>• Architect and build a functional reference implementation.</li><li>• Write unit and integration tests.</li>";
  $("#blueprintBullet").textContent = `• Implemented ${skillOrReq} solution with automated testing and live deployment.`;

  const defaultChecklist = [
    "Create GitHub repository with README and architecture diagram",
    "Write clean, modular code with unit tests",
    "Deploy demo or configure CI/CD pipeline",
    "Verify performance and add to Master Profile"
  ];
  const checkList = $("#blueprintChecklist");
  checkList.innerHTML = "";
  defaultChecklist.forEach(c => {
    const row = document.createElement("label");
    row.className = "flex-row align-center gap-2 mb-1";
    row.innerHTML = `<input type="checkbox"> <span>${escapeHtml(c)}</span>`;
    checkList.appendChild(row);
  });

  try {
    if (state.activeJob) {
      const data = await API.request(`/jobs/${state.activeJob.id}/learning-gap?req=${encodeURIComponent(skillOrReq)}`);
      if (data && data.blueprint) {
        const bp = data.blueprint;
        $("#blueprintProjectTitle").textContent = bp.title || `Mini-Project: ${skillOrReq}`;
        $("#blueprintEstHours").textContent = `Est: ${bp.estimated_hours || "10–12"} hours`;
        $("#blueprintOverview").textContent = bp.architecture_overview || bp.overview || "";

        const delivList = $("#blueprintDeliverables");
        delivList.innerHTML = "";
        (bp.deliverables || []).forEach(d => {
          const li = document.createElement("li");
          li.textContent = `• ${d}`;
          delivList.appendChild(li);
        });

        $("#blueprintBullet").textContent = bp.proposed_resume_bullet || `• Implemented ${skillOrReq} solution with automated testing and live deployment.`;

        const bpChecklist = bp.checklist && bp.checklist.length > 0 ? bp.checklist : defaultChecklist;
        checkList.innerHTML = "";
        bpChecklist.forEach(c => {
          const row = document.createElement("label");
          row.className = "flex-row align-center gap-2 mb-1";
          row.innerHTML = `<input type="checkbox"> <span>${escapeHtml(c)}</span>`;
          checkList.appendChild(row);
        });
      }
    }
  } catch (_) {
    // Fallback blueprint is active
  }
  drawIcons();
}

async function handleExportWithPreCheck(format) {
  if (!state.activeJob || !state.activeVersion) {
    return toast("Select a version snapshot first.", "error");
  }

  try {
    toast("Verifying resume quality & consistency...");
    const check = await API.request(
      `/jobs/${state.activeJob.id}/versions/${state.activeVersion.id}/pre-export-check`
    );

    const warnings = check.warnings || [];
    if (warnings.length === 0 || check.can_export) {
      return executeExportDownload(state.activeJob.id, state.activeVersion.id, format);
    }

    pendingExportAction = () => executeExportDownload(state.activeJob.id, state.activeVersion.id, format);
    const modal = $("#preExportModal");
    const list = $("#preExportWarningsList");
    list.innerHTML = "";

    warnings.forEach((w) => {
      const card = document.createElement("div");
      card.className = `pre-export-issue-card ${w.severity === "DANGER" ? "danger" : "warning"}`;
      card.innerHTML = `
        <div class="flex-row justify-between align-center mb-1">
          <strong>${escapeHtml(w.item || "Consistency Notice")}</strong>
          <span class="evidence-status-pill ${w.severity === "DANGER" ? "missing" : "partial"}">${escapeHtml(w.severity || "WARNING")}</span>
        </div>
        <p class="text-xs text-muted mb-1">${escapeHtml(w.issue)}</p>
        <div class="dimension-why text-xs">
          <strong>WHY:</strong> ${escapeHtml(w.explanation || "Addressing this improves recruiter evaluation.")}
        </div>
      `;
      list.appendChild(card);
    });

    modal.classList.remove("hidden");
    drawIcons();
  } catch (err) {
    executeExportDownload(state.activeJob.id, state.activeVersion.id, format);
  }
}

async function executeExportDownload(jobId, versionId, format) {
  $("#preExportModal")?.classList.add("hidden");
  try {
    toast(`Preparing ${format.toUpperCase()} export...`);
    const blob = await API.request(
      `/jobs/${jobId}/versions/${versionId}/export?format=${format}&template=${state.activeVersion.template_name}`,
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${state.user?.full_name || "Resume"}_${state.activeVersion.template_name}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
    toast(`${format.toUpperCase()} downloaded successfully.`);
    await loadBillingSummary();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

function checkAndShowOnboarding() {
  const seen = localStorage.getItem("smartresume_seen_onboarding");
  const p = state.profile;
  const isFresh = !p || ((!p.experiences || p.experiences.length === 0) && (!p.skills || p.skills.length === 0));
  if (!seen && isFresh) {
    const modal = $("#onboardingModal");
    if (modal) modal.classList.remove("hidden");
    drawIcons();
  }
}

function wireOnboardingModal() {
  $("#dismissOnboardingBtn")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
  });
  $("#closeOnboardingModalBtn")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
  });
  $("#onboardImportCard")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
    navigateToTab("profile");
    openImportModal();
  });
  $("#onboardManualCard")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
    navigateToTab("profile");
  });
  $("#onboardDemoCard")?.addEventListener("click", async () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
    navigateToTab("fit");
    $("#targetJobTitle").value = "Senior Backend Engineer";
    $("#targetCompany").value = "Razorpay";
    $("#targetJobDesc").value = "We are looking for a Senior Backend Engineer with 3+ years experience building scalable microservices in Python / Go, designing RESTful APIs, utilizing Redis caching, PostgreSQL database optimization, Docker containerization, and AWS cloud infrastructure.";
    toast("Loaded demo target job. Click 'Analyze ATS Fit' to test!");
  });
}

// ==========================================================================
// 1. EVIDENCE VAULT MODULE
// ==========================================================================
let currentEvidenceFilter = "ALL";
let cachedEvidenceItems = [];

function wireEvidenceVault() {
  $("#syncEvidenceBtn")?.addEventListener("click", async () => {
    const btn = $("#syncEvidenceBtn");
    setButtonLoading(btn, true, "Syncing...");
    try {
      const res = await API.request("/evidence-vault/sync", { method: "POST" });
      toast(res.message || "Synced items into Evidence Vault.");
      await loadEvidenceVault();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false, "Sync from Master Profile");
      drawIcons();
    }
  });

  $$("[data-evidence-filter]").forEach((chip) => {
    chip.addEventListener("click", () => {
      $$("[data-evidence-filter]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      currentEvidenceFilter = chip.dataset.evidenceFilter;
      renderEvidenceVaultItems();
    });
  });

  $("#addEvidenceBtn")?.addEventListener("click", async () => {
    const title = prompt("Enter Evidence Title (e.g. Led payment API redesign):");
    if (!title) return;
    const desc = prompt("Enter accomplishment details / metrics:") || "";
    try {
      await API.request("/evidence-vault", {
        method: "POST",
        body: { title, description: desc, type: "PROJECT", source: "manual", verification_status: "VERIFIED" },
      });
      toast("Evidence added to vault.");
      await loadEvidenceVault();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function loadEvidenceVault() {
  const container = $("#evidenceVaultList");
  if (!container) return;
  try {
    cachedEvidenceItems = await API.request("/evidence-vault");
    renderEvidenceVaultItems();
  } catch (err) {
    container.innerHTML = `<p class="text-danger text-center py-3">${escapeHtml(err.message)}</p>`;
  }
}

function renderEvidenceVaultItems() {
  const container = $("#evidenceVaultList");
  if (!container) return;
  container.innerHTML = "";

  let items = cachedEvidenceItems;
  if (currentEvidenceFilter !== "ALL") {
    items = items.filter((it) => (it.type || "").toUpperCase() === currentEvidenceFilter);
  }

  if (items.length === 0) {
    container.innerHTML = `
      <div class="p-4 text-center text-muted">
        <p>No evidence items found for this category.</p>
        <p class="text-xs mt-1">Click "Sync from Master Profile" to extract verified records.</p>
      </div>
    `;
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "evidence-card";
    const statusClass = (item.verification_status || "VERIFIED").toLowerCase();
    card.innerHTML = `
      <div class="evidence-header">
        <div>
          <span class="badge-sub">${escapeHtml(item.type)}</span>
          <strong class="ml-2">${escapeHtml(item.title)}</strong>
        </div>
        <span class="evidence-badge ${statusClass}">${escapeHtml(item.verification_status)}</span>
      </div>
      <p class="text-sm text-muted">${escapeHtml(item.description || item.context || "No detailed notes.")}</p>
      <div class="flex-between text-xs text-muted mt-2 border-t pt-2">
        <span>Context: ${escapeHtml(item.context || "General")}</span>
        <span>Confidence: ${Math.round((item.confidence || 1.0) * 100)}%</span>
      </div>
    `;
    container.appendChild(card);
  });
  drawIcons();
}

// ==========================================================================
// 2. JOB RADAR MODULE
// ==========================================================================
let currentRadarCategory = "ALL";
let cachedRadarListings = [];

function wireJobRadar() {
  $("#radarSearchBtn")?.addEventListener("click", () => loadJobRadar());

  $$("[data-radar-category]").forEach((chip) => {
    chip.addEventListener("click", () => {
      $$("[data-radar-category]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      currentRadarCategory = chip.dataset.radarCategory;
      renderJobRadarListings();
    });
  });
}

async function loadJobRadar() {
  const container = $("#jobRadarList");
  if (!container) return;
  const q = $("#radarQueryInput")?.value || "";
  const loc = $("#radarLocationInput")?.value || "";
  const dom = $("#radarDomainSelect")?.value || "";

  try {
    container.innerHTML = `<p class="text-muted text-center py-4">Scanning live opportunities...</p>`;
    const res = await API.request(`/job-radar?query=${encodeURIComponent(q)}&location=${encodeURIComponent(loc)}&domain=${encodeURIComponent(dom)}`);
    cachedRadarListings = res.listings || [];
    renderJobRadarListings();
  } catch (err) {
    container.innerHTML = `<p class="text-danger text-center py-3">${escapeHtml(err.message)}</p>`;
  }
}

function renderJobRadarListings() {
  const container = $("#jobRadarList");
  if (!container) return;
  container.innerHTML = "";

  let list = cachedRadarListings;
  if (currentRadarCategory !== "ALL") {
    list = list.filter((it) => it.match_category === currentRadarCategory);
  }

  if (list.length === 0) {
    container.innerHTML = `<p class="text-muted text-center py-4">No matching roles found on radar.</p>`;
    return;
  }

  list.forEach((item) => {
    const card = document.createElement("div");
    card.className = "panel mb-3";
    const catLabels = {
      STRONG_MATCH: { label: "Strong Match", color: "#10b981" },
      REACH: { label: "Reach Opportunity", color: "#3b82f6" },
      STRETCH: { label: "Stretch", color: "#f59e0b" },
      BACKUP: { label: "Backup Match", color: "#8b5cf6" },
    };
    const cat = catLabels[item.match_category] || { label: item.match_category, color: "#64748b" };

    card.innerHTML = `
      <div class="flex-between">
        <div>
          <h4>${escapeHtml(item.title)}</h4>
          <p class="text-sm text-muted"><strong>${escapeHtml(item.company)}</strong> • ${escapeHtml(item.location)} • ${escapeHtml(item.salary_range)}</p>
        </div>
        <div class="text-right">
          <span class="badge-pill" style="background: rgba(59, 130, 246, 0.15); color: ${cat.color}; font-weight: 700;">${cat.label} (${item.match_score}%)</span>
          <p class="text-xs text-muted mt-1">${escapeHtml(item.posted_date)}</p>
        </div>
      </div>
      <p class="text-sm mt-2">${escapeHtml(item.description)}</p>
      <div class="skills-chip-grid mt-3">
        ${(item.required_skills || []).map((s) => `<span class="skill-chip active">${escapeHtml(s)}</span>`).join("")}
      </div>
      <div class="flex-row gap-2 mt-3 pt-3 border-t">
        <button class="primary-btn sm apply-radar-btn" data-job-title="${escapeHtml(item.title)}" data-job-comp="${escapeHtml(item.company)}" data-job-desc="${escapeHtml(item.description)}">
          <i data-lucide="sparkles"></i><span>Match & Tailor Application</span>
        </button>
        ${item.direct_apply_url ? `<a href="${item.direct_apply_url}" target="_blank" class="secondary-btn sm"><i data-lucide="external-link"></i><span>Direct Apply</span></a>` : ""}
      </div>
    `;

    card.querySelector(".apply-radar-btn")?.addEventListener("click", () => {
      navigateToTab("fit");
      $("#targetJobTitle").value = item.title;
      $("#targetCompany").value = item.company;
      $("#targetJobDesc").value = item.description;
      toast(`Loaded ${item.title} into Job Match & Fit!`);
    });

    container.appendChild(card);
  });
  drawIcons();
}

// ==========================================================================
// 3. SMARTAPPLY TAB MODULE
// ==========================================================================
function wireSmartApplyTab() {
  $$(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.copyTarget;
      const el = $(`#${targetId}`);
      if (el) {
        navigator.clipboard.writeText(el.textContent.trim()).then(() => toast("Copied answer to clipboard!"));
      }
    });
  });
}

async function loadSmartApplyAnswers() {
  try {
    const data = await API.request("/smartapply/field-answers", {
      method: "POST",
      body: { fields: ["why_company", "achievement"] },
    });
    if (data.all_available_answers) {
      if ($("#previewWhyCompany") && data.all_available_answers.why_company) {
        $("#previewWhyCompany").textContent = data.all_available_answers.why_company;
      }
      if ($("#previewAccomplishment") && data.all_available_answers.achievement) {
        $("#previewAccomplishment").textContent = data.all_available_answers.achievement;
      }
    }
  } catch (_) {}
}

// ==========================================================================
// 4. INTERVIEW COPILOT MODULE
// ==========================================================================
let activeInterviewSessionId = null;

function wireInterviewCopilot() {
  $("#startInterviewForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const role = $("#interviewRoleInput").value.trim();
    const company = $("#interviewCompanyInput").value.trim();
    const mode = $("#interviewModeSelect").value;

    try {
      toast("Initializing AI Interview Copilot...");
      const session = await API.request("/interview/sessions", {
        method: "POST",
        body: { target_role: role, target_company: company, session_mode: mode },
      });
      activeInterviewSessionId = session.id;
      renderActiveInterviewSession(session);
      await loadInterviewSessions();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#interviewTurnForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!activeInterviewSessionId) return;

    const input = $("#candidateAnswerInput");
    const text = input.value.trim();
    if (!text) return;

    appendInterviewMsg("user", text);
    input.value = "";

    try {
      const turnRes = await API.request(`/interview/sessions/${activeInterviewSessionId}/turns`, {
        method: "POST",
        body: { message_text: text },
      });
      appendInterviewMsg("ai", turnRes.ai_response);
      if (turnRes.turn_feedback) {
        toast(turnRes.turn_feedback.star_assessment || "Response recorded.");
      }
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#endInterviewBtn")?.addEventListener("click", async () => {
    if (!activeInterviewSessionId) return;
    try {
      toast("Evaluating full interview performance...");
      const evaluation = await API.request(`/interview/sessions/${activeInterviewSessionId}/complete`, { method: "POST" });
      appendInterviewMsg("ai", `🏁 **Interview Completed! Readiness Verdict: ${evaluation.readiness_level}**\n\n• **Strengths**: ${evaluation.strong_areas.join(", ")}\n• **Needs Practice**: ${evaluation.needs_practice.join(", ")}`);
      $("#endInterviewBtn")?.classList.add("hidden");
      $("#interviewTurnForm")?.classList.add("hidden");
      toast("Readiness evaluation generated!");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function loadInterviewSessions() {
  const container = $("#interviewSessionsList");
  if (!container) return;
  try {
    const sessions = await API.request("/interview/sessions");
    if (sessions.length === 0) {
      container.innerHTML = `<p class="text-muted text-xs">No previous interview sessions yet.</p>`;
      return;
    }
    container.innerHTML = sessions.map((s) => `
      <div class="panel p-2 mb-2 text-xs cursor-pointer" onclick="resumeInterviewSession(${s.id})">
        <strong>${escapeHtml(s.target_role || "Role")}</strong> at ${escapeHtml(s.target_company || "Company")}
        <div class="flex-between text-muted mt-1">
          <span>${s.status}</span>
          <span>Score: ${s.readiness_score}/100</span>
        </div>
      </div>
    `).join("");
  } catch (_) {}
}

async function resumeInterviewSession(sessionId) {
  try {
    const session = await API.request(`/interview/sessions/${sessionId}`);
    activeInterviewSessionId = session.id;
    renderActiveInterviewSession(session);
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderActiveInterviewSession(session) {
  $("#activeInterviewTitle").textContent = `${session.target_role} at ${session.target_company}`;
  $("#interviewStatusPill").textContent = session.status;
  $("#endInterviewBtn")?.classList.remove("hidden");
  $("#interviewTurnForm")?.classList.remove("hidden");

  const chatBox = $("#interviewChatBox");
  chatBox.innerHTML = "";

  (session.messages || []).forEach((m) => {
    appendInterviewMsg(m.sender.toLowerCase() === "user" ? "user" : "ai", m.message_text);
  });
}

function appendInterviewMsg(sender, text) {
  const chatBox = $("#interviewChatBox");
  if (!chatBox) return;
  const msgEl = document.createElement("div");
  msgEl.className = `chat-msg ${sender}`;
  msgEl.innerHTML = text.replace(/\n/g, "<br>");
  chatBox.appendChild(msgEl);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// ==========================================================================
// 5. CAREER INSIGHTS MODULE
// ==========================================================================
function wireCareerInsights() {
  $("#refreshInsightsBtn")?.addEventListener("click", () => loadCareerInsights());
}

async function loadCareerInsights() {
  try {
    const data = await API.request("/career-insights");
    if ($("#insightsDomain")) $("#insightsDomain").textContent = data.target_domain;
    if ($("#insightsLevel")) $("#insightsLevel").textContent = data.current_level;
    if ($("#insightsVerifiedCount")) $("#insightsVerifiedCount").textContent = `${data.verified_evidence_count} Verified`;

    // Render demand grid
    const grid = $("#skillsDemandGrid");
    if (grid && data.skills_in_high_demand) {
      grid.innerHTML = data.skills_in_high_demand.map((s) => `
        <div class="skill-demand-card">
          <div class="flex-between">
            <strong>${escapeHtml(s.skill)}</strong>
            <span class="evidence-badge ${s.user_status.includes("VERIFIED") ? "verified" : "profile_only"}">${escapeHtml(s.user_status.replace("IN_PROFILE_", ""))}</span>
          </div>
          <span class="text-xs text-muted">Demand: ${escapeHtml(s.demand_level)} • ${escapeHtml(s.category)}</span>
          <p class="text-xs mt-1">${escapeHtml(s.suggested_action)}</p>
        </div>
      `).join("");
    }

    // Render pathway
    const pathwayBox = $("#careerPathwayDetails");
    if (pathwayBox && data.career_pathway) {
      pathwayBox.innerHTML = `
        <div class="mt-2 text-sm">
          <p><strong>Pathway:</strong> ${escapeHtml(data.career_pathway.current_level)} → <span class="text-primary font-bold">${escapeHtml(data.career_pathway.target_level)}</span></p>
          <p class="text-muted text-xs mt-1">Timeline: ${escapeHtml(data.career_pathway.timeline_estimate)}</p>
          <h5 class="mt-3 mb-1">Key Skills to Master:</h5>
          <div class="skills-chip-grid">
            ${(data.career_pathway.skills_to_acquire || []).map((sk) => `<span class="skill-chip">${escapeHtml(sk)}</span>`).join("")}
          </div>
        </div>
      `;
    }
  } catch (_) {}
}

// ==========================================================================
// 6. NOTIFICATIONS MODULE
// ==========================================================================
function wireNotifications() {
  $("#notifBellBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    $("#notifDropdown")?.classList.toggle("hidden");
  });

  document.addEventListener("click", () => {
    $("#notifDropdown")?.classList.add("hidden");
  });

  $("#notifDropdown")?.addEventListener("click", (e) => e.stopPropagation());

  $("#markAllNotifsBtn")?.addEventListener("click", async () => {
    try {
      await API.request("/notifications/read-all", { method: "POST" });
      await loadNotifications();
      toast("All notifications marked as read.");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function loadNotifications() {
  try {
    const res = await API.request("/notifications");
    const badge = $("#notifBadge");
    const list = $("#notifList");

    if (badge) {
      badge.textContent = res.unread_count;
      badge.classList.toggle("hidden", res.unread_count === 0);
    }

    if (list) {
      if (res.notifications.length === 0) {
        list.innerHTML = `<p class="text-xs text-muted p-3 text-center">No notifications.</p>`;
      } else {
        list.innerHTML = res.notifications.map((n) => `
          <div class="notif-item ${n.is_read ? "" : "unread"}" onclick="handleNotifClick(${n.id}, '${escapeHtml(n.action_url)}')">
            <div class="notif-item-title">${escapeHtml(n.title)}</div>
            <div class="text-muted">${escapeHtml(n.message)}</div>
            <div class="notif-item-time">${new Date(n.created_at).toLocaleDateString()}</div>
          </div>
        `).join("");
      }
    }
  } catch (_) {}
}

async function handleNotifClick(notifId, actionUrl) {
  try {
    await API.request(`/notifications/${notifId}/read`, { method: "POST" });
    await loadNotifications();
    if (actionUrl && actionUrl.startsWith("#")) {
      navigateToTab(actionUrl.replace("#", ""));
    }
  } catch (_) {}
}

// ==========================================================================
// 7. PRO TRIAL MODULE
// ==========================================================================
function wireProTrial() {
  $("#startTrialBtn")?.addEventListener("click", async () => {
    const btn = $("#startTrialBtn");
    setButtonLoading(btn, true, "Activating Trial...");
    try {
      const res = await API.request("/payments/start-trial", { method: "POST" });
      toast(res.message || "7-Day Pro Trial activated!");
      state.user = await API.request("/users/profile");
      renderUserBar();
      await loadBillingSummary();
      navigateToTab("evidence-vault");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false, "Start 7-Day Pro Trial (₹0)");
      drawIcons();
    }
  });
}

// ==========================================================================
// 8. INTERNATIONAL RULES MODULE
// ==========================================================================
function wireInternationalRules() {
  $("#countryRulesSelect")?.addEventListener("change", async (e) => {
    const country = e.target.value;
    try {
      const rules = await API.request(`/smartbuild/country-rules/${country}`);
      const disp = $("#countryRulesDisplay");
      if (disp) {
        disp.innerHTML = `
          <div class="rules-detail">
            <strong>${escapeHtml(rules.name)} CV Guidelines:</strong>
            <p class="mt-1">📸 <strong>Photo:</strong> ${rules.photo_allowed ? "Accepted / Customary" : "Strictly Disallowed (Anti-discrimination laws)"}</p>
            <p>📄 <strong>Recommended Length:</strong> ${escapeHtml(rules.recommended_pages)}</p>
            <p>✍️ <strong>Spelling:</strong> ${escapeHtml(rules.spelling)}</p>
            <p class="text-xs text-muted mt-2">${escapeHtml(rules.photo_guidance)}</p>
          </div>
        `;
      }
    } catch (_) {}
  });
}

// ==========================================================================
// 9. APPLICATION PACK MODAL (13 ASSETS)
// ==========================================================================
let currentAppPackData = null;

function wireApplicationPackModal() {
  $("#closeAppPackModalBtn")?.addEventListener("click", () => {
    $("#applicationPackModal")?.classList.add("hidden");
  });
  $("#dismissAppPackBtn")?.addEventListener("click", () => {
    $("#applicationPackModal")?.classList.add("hidden");
  });

  $$(".pack-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".pack-tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderPackTabContent(btn.dataset.packView);
    });
  });
}

async function openApplicationPack(versionId) {
  const modal = $("#applicationPackModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  const content = $("#packTabContent");
  content.innerHTML = `<p class="text-muted text-center py-4">Generating complete 13-asset Application Pack...</p>`;

  try {
    currentAppPackData = await API.request(`/application-pack/${versionId}`);
    renderPackTabContent("cover-letter");
  } catch (err) {
    content.innerHTML = `<p class="text-danger text-center py-3">${escapeHtml(err.message)}</p>`;
  }
}

function renderPackTabContent(viewName) {
  const content = $("#packTabContent");
  if (!content || !currentAppPackData) return;

  if (viewName === "cover-letter") {
    content.innerHTML = `
      <div class="flex-between mb-2">
        <strong>Tailored Cover Letter</strong>
        <button class="text-btn text-xs" onclick="navigator.clipboard.writeText(currentAppPackData.cover_letter).then(() => toast('Cover letter copied!'))">Copy to Clipboard</button>
      </div>
      <div class="p-3 bg-surface border rounded text-sm" style="white-space: pre-wrap; font-family: monospace;">${escapeHtml(currentAppPackData.cover_letter)}</div>
    `;
  } else if (viewName === "recruiter-email") {
    const em = currentAppPackData.recruiter_email || {};
    content.innerHTML = `
      <div class="flex-between mb-2">
        <strong>Direct Recruiter Email Pitch</strong>
        <a href="${em.gmail_url || '#'}" target="_blank" class="primary-btn sm"><i data-lucide="external-link"></i><span>Open in Gmail</span></a>
      </div>
      <div class="form-grid mb-2">
        <label>Subject Line<input value="${escapeHtml(em.subject || '')}" readonly></label>
      </div>
      <div class="p-3 bg-surface border rounded text-sm" style="white-space: pre-wrap;">${escapeHtml(em.body || '')}</div>
    `;
  } else if (viewName === "portal-answers") {
    const ans = currentAppPackData.application_answers || [];
    content.innerHTML = `
      <div class="mb-2"><strong>Custom Application Form Answers</strong></div>
      ${ans.map((a) => `
        <div class="panel p-3 mb-2">
          <strong>${escapeHtml(a.question)}</strong>
          <p class="text-sm mt-1">${escapeHtml(a.answer)}</p>
          <div class="flex-between text-xs text-muted mt-2">
            <span>Grounding: ${escapeHtml(a.grounding)}</span>
            <button class="text-btn text-xs" onclick="navigator.clipboard.writeText('${escapeHtml(a.answer).replace(/'/g, "\\'")}').then(() => toast('Answer copied!'))">Copy</button>
          </div>
        </div>
      `).join("")}
    `;
  } else if (viewName === "follow-up") {
    const fu = currentAppPackData.follow_up_strategy || {};
    const ty = currentAppPackData.thank_you_note || "";
    content.innerHTML = `
      <div class="panel mb-3">
        <strong>Follow-Up Strategy (Target Date: ${escapeHtml(fu.suggested_date || 'In 6 days')})</strong>
        <div class="p-3 bg-surface border rounded text-sm mt-2" style="white-space: pre-wrap;">${escapeHtml(fu.template || '')}</div>
      </div>
      <div class="panel">
        <strong>Post-Interview Thank You Note</strong>
        <div class="p-3 bg-surface border rounded text-sm mt-2" style="white-space: pre-wrap;">${escapeHtml(ty)}</div>
      </div>
    `;
  } else if (viewName === "interview-prep") {
    const ip = currentAppPackData.interview_prep_brief || {};
    content.innerHTML = `
      <div class="panel mb-3">
        <strong>Resume Claims You Will Be Asked to Defend:</strong>
        <ul class="text-sm mt-2">
          ${(ip.claims_to_defend || []).map((c) => `<li class="mb-1">• ${escapeHtml(c)}</li>`).join("")}
        </ul>
      </div>
      <div class="panel">
        <strong>Anticipated High-Probability Interview Questions:</strong>
        <ul class="text-sm mt-2">
          ${(ip.likely_questions || []).map((q) => `<li class="mb-1">❓ ${escapeHtml(q)}</li>`).join("")}
        </ul>
      </div>
    `;
  }
  drawIcons();
}

// ==========================================================================
// 10. RESUME TEMPLATES MODULE & CUSTOMIZER
// ==========================================================================
let activePreviewTemplateId = null;
let pendingUpgradeTemplateId = null;

function wireTemplates() {
  // Intent filter pills
  $$("#intentPillsContainer .intent-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      $$("#intentPillsContainer .intent-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.templateIntent = pill.dataset.intent || "ALL";
      filterAndRenderTemplates();
    });
  });

  // Category filter chips
  $$("#categoryFilterBar .filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      $$("#categoryFilterBar .filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.templateCategory = chip.dataset.cat || "ALL";
      filterAndRenderTemplates();
    });
  });

  // Tier filter chips
  $$("[data-tier]").forEach((chip) => {
    chip.addEventListener("click", () => {
      $$("[data-tier]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.templateTier = chip.dataset.tier || "ALL";
      filterAndRenderTemplates();
    });
  });

  // Search input
  const searchInput = $("#templateSearchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.templateSearch = (e.target.value || "").trim().toLowerCase();
      filterAndRenderTemplates();
    });
  }

  // Reset filters
  $("#resetTemplateFiltersBtn")?.addEventListener("click", () => {
    state.templateIntent = "ALL";
    state.templateCategory = "ALL";
    state.templateTier = "ALL";
    state.templateSearch = "";
    if (searchInput) searchInput.value = "";
    $$("#intentPillsContainer .intent-pill").forEach((p) => p.classList.toggle("active", p.dataset.intent === "ALL"));
    $$("#categoryFilterBar .filter-chip").forEach((c) => c.classList.toggle("active", c.dataset.cat === "ALL"));
    $$("[data-tier]").forEach((c) => c.classList.toggle("active", c.dataset.tier === "ALL"));
    filterAndRenderTemplates();
    toast("Filters reset to default.");
  });

  // Compare selected button
  $("#openCompareModalBtn")?.addEventListener("click", () => openTemplateCompareModal());
  $("#clearCompareBtn")?.addEventListener("click", () => {
    state.selectedCompareIds.clear();
    updateCompareCountBadge();
    filterAndRenderTemplates();
    openTemplateCompareModal();
  });

  // Modal close buttons
  $("#closeTemplatePreviewBtn")?.addEventListener("click", () => $("#templatePreviewModal")?.classList.add("hidden"));
  $("#closeTemplateCompareBtn")?.addEventListener("click", () => $("#templateCompareModal")?.classList.add("hidden"));
  $("#closeTemplateUpgradeBtn")?.addEventListener("click", () => $("#templateUpgradeModal")?.classList.add("hidden"));

  // Recommended Hero buttons
  $("#recHeroPreviewBtn")?.addEventListener("click", () => {
    const recId = state.templateRecommendation?.recommended_template_id || "technical_ats";
    openTemplatePreview(recId);
  });
  $("#recHeroUseBtn")?.addEventListener("click", () => {
    const recId = state.templateRecommendation?.recommended_template_id || "technical_ats";
    selectActiveTemplate(recId);
  });

  // Customizer controls
  $("#customizerFontSize")?.addEventListener("change", (e) => {
    state.customizer.fontSize = e.target.value;
    updateCustomizerStyles();
  });
  $("#customizerSpacing")?.addEventListener("change", (e) => {
    state.customizer.spacing = e.target.value;
    updateCustomizerStyles();
  });

  // Preview modal actions
  $("#previewModalUseBtn")?.addEventListener("click", () => {
    if (activePreviewTemplateId) selectActiveTemplate(activePreviewTemplateId);
  });
  $("#previewModalCompareBtn")?.addEventListener("click", () => {
    if (activePreviewTemplateId) {
      state.selectedCompareIds.add(activePreviewTemplateId);
      updateCompareCountBadge();
      filterAndRenderTemplates();
      $("#templatePreviewModal")?.classList.add("hidden");
      openTemplateCompareModal();
    }
  });

  // Upgrade modal actions
  $("#upgradeModalPreviewBtn")?.addEventListener("click", () => {
    $("#templateUpgradeModal")?.classList.add("hidden");
    if (pendingUpgradeTemplateId) openTemplatePreview(pendingUpgradeTemplateId);
  });
  $("#upgradeModalActionBtn")?.addEventListener("click", async () => {
    $("#templateUpgradeModal")?.classList.add("hidden");
    if (!state.user || state.user.plan_name === "FREE") {
      try {
        toast("Activating 7-Day Pro Trial...");
        const res = await API.request("/payments/start-trial", { method: "POST" });
        toast(res.message || "7-Day Pro Trial activated!");
        state.user = await API.request("/users/profile");
        renderUserBar();
        await loadBillingSummary();
        if (pendingUpgradeTemplateId) {
          selectActiveTemplate(pendingUpgradeTemplateId);
        }
      } catch (err) {
        toast("Navigating to billing plans...", "info");
        navigateToTab("billing");
      }
    } else {
      navigateToTab("billing");
    }
  });

  // Sync with Application Builder template dropdown
  const appBuilderSelector = $("#templateSelector");
  if (appBuilderSelector) {
    appBuilderSelector.addEventListener("change", (e) => {
      const tId = e.target.value;
      if (tId) {
        state.activeTemplateId = tId;
        localStorage.setItem("activeTemplateId", tId);
        syncActiveTemplateDisplay();
      }
    });
  }

  // Expose global methods
  window.selectActiveTemplate = selectActiveTemplate;
  window.openTemplatePreview = openTemplatePreview;
}

async function loadTemplatesCatalogOnly() {
  try {
    const [catalog, rec] = await Promise.all([
      API.request("/templates"),
      API.request("/templates/recommend").catch(() => null),
    ]);
    state.templates = catalog || [];
    state.templateRecommendation = rec;
  } catch (_) {}
}

async function loadTemplatesView() {
  const grid = $("#templatesGrid");
  if (grid && (!state.templates || state.templates.length === 0)) {
    grid.innerHTML = `<div class="span-all text-center text-muted py-5"><i data-lucide="loader"></i><p class="mt-2">Loading ATS template catalog...</p></div>`;
    drawIcons();
  }

  try {
    const [catalog, rec] = await Promise.all([
      API.request("/templates"),
      API.request("/templates/recommend").catch(() => null),
    ]);
    state.templates = catalog || [];
    state.templateRecommendation = rec;

    // Render hero recommendation
    renderRecommendationHero(rec);

    // Render template cards
    filterAndRenderTemplates();
    syncActiveTemplateDisplay();
  } catch (err) {
    if (grid) {
      grid.innerHTML = `<div class="span-all alert-info"><p>Failed to load template catalog: ${escapeHtml(err.message)}</p></div>`;
    }
  }
}

function renderRecommendationHero(rec) {
  const card = $("#recHeroCard");
  if (!card) return;

  if (!rec || !rec.recommended_template) {
    card.classList.add("hidden");
    return;
  }

  card.classList.remove("hidden");
  const tpl = rec.recommended_template;
  $("#recHeroTitle").textContent = tpl.name;
  $("#recHeroReason").textContent = rec.recommendation_reason || tpl.description;
  
  const countryEl = $("#recHeroCountryText");
  if (countryEl && rec.country_guidance) {
    const cg = rec.country_guidance;
    countryEl.textContent = `${cg.name} (${cg.standard}): ${cg.photo_rule}. Recommended length: ${cg.recommended_pages}.`;
  }
}

function filterAndRenderTemplates() {
  const grid = $("#templatesGrid");
  if (!grid) return;

  let items = state.templates || [];

  // 1. Intent filter
  if (state.templateIntent && state.templateIntent !== "ALL") {
    items = items.filter((t) => {
      if (state.templateIntent === "FIRST_JOB") {
        return t.template_id === "campus_fresher" || t.category === "Early Career" || (t.best_for_level || []).some(l => l.includes("STUDENT") || l.includes("EARLY"));
      }
      if (state.templateIntent === "SPECIFIC_JOB") {
        return ["technical_ats", "clean_professional", "finance_professional", "healthcare_pharmacy", "consulting_management"].includes(t.template_id);
      }
      if (state.templateIntent === "CURRENT_CAREER") {
        return ["experienced_professional", "classic_ats", "business_professional"].includes(t.template_id);
      }
      if (state.templateIntent === "ACADEMIC") {
        return t.template_id === "academic_research" || t.category === "Academic / Research";
      }
      if (state.templateIntent === "EXECUTIVE") {
        return t.template_id === "executive" || t.category === "Executive";
      }
      return true;
    });
  }

  // 2. Category filter
  if (state.templateCategory && state.templateCategory !== "ALL") {
    items = items.filter((t) => (t.category || "").toLowerCase() === state.templateCategory.toLowerCase());
  }

  // 3. Tier filter
  if (state.templateTier && state.templateTier !== "ALL") {
    items = items.filter((t) => (t.tier || "").toUpperCase() === state.templateTier.toUpperCase());
  }

  // 4. Search query
  if (state.templateSearch) {
    const q = state.templateSearch.toLowerCase();
    items = items.filter((t) => {
      const inName = (t.name || "").toLowerCase().includes(q);
      const inDesc = (t.description || "").toLowerCase().includes(q);
      const inCat = (t.category || "").toLowerCase().includes(q);
      const inRoles = (t.best_for_roles || []).some((r) => r.toLowerCase().includes(q));
      const inDomains = (t.best_for_domains || []).some((d) => d.toLowerCase().includes(q));
      return inName || inDesc || inCat || inRoles || inDomains;
    });
  }

  if (items.length === 0) {
    grid.innerHTML = `
      <div class="span-all empty-state-card">
        <i data-lucide="layout-template"></i>
        <h4>No matching templates found</h4>
        <p>Try adjusting your category, intent, or search keyword filter to see other options.</p>
        <button class="secondary-btn sm mt-2" onclick="$('#resetTemplateFiltersBtn').click()">Reset Filters</button>
      </div>
    `;
    drawIcons();
    return;
  }

  grid.innerHTML = "";
  const recommendedId = state.templateRecommendation?.recommended_template_id;

  items.forEach((t) => {
    const isRecommended = t.template_id === recommendedId;
    const isActive = t.template_id === state.activeTemplateId;
    const isChecked = state.selectedCompareIds.has(t.template_id);
    const isPro = t.tier === "PRO";

    const card = document.createElement("div");
    card.className = `template-card ${isActive ? "active" : ""}`;
    card.dataset.templateId = t.template_id;

    // Mini paper preview representation
    const accent = t.accent_color || "#1e3a8a";
    card.innerHTML = `
      <div class="template-card-thumb">
        <div class="mini-paper">
          <div class="mini-header" style="border-bottom: 2px solid ${accent};">
            <div class="mini-name-bar" style="background: ${accent};"></div>
            <div class="mini-line" style="width: 70%; margin: 2px auto;"></div>
          </div>
          <div class="mini-body">
            <div class="mini-section-bar" style="background: ${accent};"></div>
            <div class="mini-line" style="width: 90%;"></div>
            <div class="mini-line" style="width: 80%;"></div>
            <div class="mini-line" style="width: 85%;"></div>
            <div class="mini-section-bar mt-1" style="background: ${accent};"></div>
            <div class="mini-line" style="width: 75%;"></div>
            <div class="mini-line" style="width: 92%;"></div>
          </div>
        </div>
        ${isRecommended ? `<span class="rec-card-badge"><i data-lucide="sparkles"></i> Recommended</span>` : ""}
      </div>
      <div class="template-card-body">
        <div class="template-card-head">
          <div class="template-title-col">
            <h4>${escapeHtml(t.name)}</h4>
            <span class="category-chip">${escapeHtml(t.category)}</span>
          </div>
          <div>
            ${isPro ? `<span class="tier-badge pro"><i data-lucide="lock"></i> PRO</span>` : `<span class="tier-badge free">FREE</span>`}
          </div>
        </div>
        <p class="template-desc">${escapeHtml(t.description)}</p>
        <div class="template-meta-row">
          <span class="meta-pill ats" title="ATS Parseability"><i data-lucide="shield-check"></i> ATS: ${t.ats_score || 99}%</span>
          <span class="meta-pill roles" title="Recommended Roles"><i data-lucide="briefcase"></i> ${(t.best_for_roles || []).slice(0, 2).join(", ")}</span>
        </div>
        ${isPro ? `<p class="text-xs text-muted mt-1 trial-hint"><i data-lucide="sparkles"></i> Included in your 7-day Pro trial</p>` : ""}
      </div>
      <div class="template-card-footer">
        <label class="compare-checkbox-label" title="Select to compare up to 4 templates">
          <input type="checkbox" data-compare-id="${t.template_id}" ${isChecked ? "checked" : ""}>
          <span>Compare</span>
        </label>
        <div class="card-btn-row">
          <button class="secondary-btn sm preview-tpl-btn" type="button" data-preview-id="${t.template_id}">
            <i data-lucide="eye"></i><span>Preview</span>
          </button>
          <button class="${isActive ? "success-btn" : "primary-btn"} sm use-tpl-btn" type="button" data-use-id="${t.template_id}">
            <i data-lucide="${isActive ? "check-circle-2" : "check"}"></i>
            <span>${isActive ? "Active" : "Use Template"}</span>
          </button>
        </div>
      </div>
    `;

    // Hook listeners
    card.querySelector(`[data-compare-id="${t.template_id}"]`).addEventListener("change", (e) => {
      if (e.target.checked) {
        if (state.selectedCompareIds.size >= 4) {
          e.target.checked = false;
          return toast("You can compare up to 4 templates at once.", "warning");
        }
        state.selectedCompareIds.add(t.template_id);
      } else {
        state.selectedCompareIds.delete(t.template_id);
      }
      updateCompareCountBadge();
    });

    card.querySelector(`[data-preview-id="${t.template_id}"]`).addEventListener("click", () => {
      openTemplatePreview(t.template_id);
    });

    card.querySelector(`[data-use-id="${t.template_id}"]`).addEventListener("click", () => {
      selectActiveTemplate(t.template_id);
    });

    grid.appendChild(card);
  });

  drawIcons();
}

function updateCompareCountBadge() {
  const countEl = $("#compareCount");
  if (countEl) countEl.textContent = state.selectedCompareIds.size;
}

async function openTemplatePreview(templateId) {
  activePreviewTemplateId = templateId;
  const t = (state.templates || []).find((x) => x.template_id === templateId) || {
    name: capitalize(templateId.replace(/_/g, " ")),
    tier: "FREE",
    category: "Professional",
    accent_color: "#1e3a8a",
    ats_score: 99,
  };

  const modal = $("#templatePreviewModal");
  if (!modal) return;

  $("#previewModalTitle").innerHTML = `<i data-lucide="layout-template"></i> ${escapeHtml(t.name)}`;
  const badgesContainer = $("#previewModalBadges");
  if (badgesContainer) {
    badgesContainer.innerHTML = `
      <span class="tier-badge ${t.tier === "PRO" ? "pro" : "free"}">${t.tier}</span>
      <span class="meta-pill ats"><i data-lucide="shield-check"></i> ATS: ${t.ats_score || 99}% Parsable</span>
      <span class="badge-sub">${escapeHtml(t.category || "Professional")}</span>
    `;
  }

  const footerInfo = $("#previewModalFooterInfo");
  if (footerInfo) {
    footerInfo.textContent = `Best for: ${(t.best_for_roles || []).join(", ") || t.category}. Single-column ATS structure.`;
  }

  const canvas = $("#templatePreviewCanvas");
  canvas.innerHTML = `<div class="p-5 text-center text-muted"><i data-lucide="loader"></i><p class="mt-2">Rendering simulated ATS candidate layout...</p></div>`;
  modal.classList.remove("hidden");
  drawIcons();

  try {
    const sample = await API.request(`/templates/${templateId}/sample`);
    renderPreviewCanvas(sample, t);
  } catch (err) {
    canvas.innerHTML = `<div class="p-4 alert-info"><p>Failed to load sample preview: ${escapeHtml(err.message)}</p></div>`;
  }
}

function renderPreviewCanvas(sample, templateMeta) {
  const canvas = $("#templatePreviewCanvas");
  if (!canvas || !sample) return;

  updateCustomizerStyles();

  const c = sample.content_json || {};
  const accent = templateMeta.accent_color || "#1e3a8a";
  const sectionOrder = templateMeta.section_order || ["EXPERIENCE", "SKILLS", "EDUCATION", "PROJECTS", "CERTIFICATIONS"];

  let html = `
    <div class="resume-paper" style="border-top: 4px solid ${accent};">
      <header class="resume-paper-header">
        <h1 style="color: ${accent};">${escapeHtml(c.candidate_name || "Jordan Taylor")}</h1>
        <p class="resume-headline">${escapeHtml(c.headline || "Senior Backend & Distributed Systems Engineer")}</p>
        <p class="resume-contact">
          ${escapeHtml(c.contact_info?.email || "jordan.taylor@example.com")} • 
          ${escapeHtml(c.contact_info?.phone || "+1 (555) 349-8201")} • 
          ${escapeHtml(c.contact_info?.location || "San Francisco, CA")} • 
          ${escapeHtml(c.contact_info?.linkedin || "linkedin.com/in/jordantaylor")}
        </p>
      </header>
  `;

  // Render sections in template's custom section order
  sectionOrder.forEach((sec) => {
    const secKey = sec.toUpperCase();
    if (secKey === "EXECUTIVE_SUMMARY" || secKey === "SUMMARY") {
      if (c.executive_summary) {
        html += `
          <section class="resume-section">
            <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">${secKey.replace(/_/g, " ")}</h3>
            <p class="text-sm mt-1">${escapeHtml(c.executive_summary)}</p>
          </section>
        `;
      }
    } else if (secKey === "EXPERIENCE" || secKey === "WORK_EXPERIENCE") {
      html += `
        <section class="resume-section">
          <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">PROFESSIONAL EXPERIENCE</h3>
          ${(c.experiences || []).map((exp) => `
            <div class="resume-entry">
              <div class="resume-entry-head">
                <strong>${escapeHtml(exp.role_title)}</strong>
                <span>${escapeHtml(exp.start_date)} – ${exp.is_current ? "Present" : escapeHtml(exp.end_date || "")}</span>
              </div>
              <div class="resume-entry-sub">
                <em>${escapeHtml(exp.company)}</em> • <span>${escapeHtml(exp.location || "")}</span>
              </div>
              <ul class="resume-bullets">
                ${(exp.bullet_points || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("")}
              </ul>
            </div>
          `).join("")}
        </section>
      `;
    } else if (secKey === "SKILLS" || secKey === "TECHNICAL_SKILLS" || secKey === "CORE_COMPETENCIES") {
      html += `
        <section class="resume-section">
          <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">${secKey.replace(/_/g, " ")}</h3>
          <div class="resume-skills-block">
            ${(c.skills || []).map((s) => {
              const name = typeof s === "string" ? s : s.name;
              return `<span class="resume-skill-tag">${escapeHtml(name)}</span>`;
            }).join(" ")}
          </div>
        </section>
      `;
    } else if (secKey === "EDUCATION") {
      html += `
        <section class="resume-section">
          <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">EDUCATION</h3>
          ${(c.education || []).map((edu) => `
            <div class="resume-entry">
              <div class="resume-entry-head">
                <strong>${escapeHtml(edu.degree)} in ${escapeHtml(edu.field_of_study)}</strong>
                <span>${escapeHtml(edu.start_date || "")} – ${escapeHtml(edu.end_date || "")}</span>
              </div>
              <div class="resume-entry-sub">
                <em>${escapeHtml(edu.institution)}</em> ${edu.grade ? `• GPA: ${escapeHtml(edu.grade)}` : ""}
              </div>
            </div>
          `).join("")}
        </section>
      `;
    } else if (secKey === "PROJECTS" || secKey === "KEY_PROJECTS") {
      html += `
        <section class="resume-section">
          <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">KEY PROJECTS</h3>
          ${(c.projects || []).map((proj) => `
            <div class="resume-entry">
              <div class="resume-entry-head">
                <strong>${escapeHtml(proj.name)}</strong>
                <span class="text-xs">${escapeHtml(proj.technologies || "")}</span>
              </div>
              <p class="text-xs text-muted">${escapeHtml(proj.description || "")}</p>
              <ul class="resume-bullets">
                ${(proj.highlights || []).map((h) => `<li>${escapeHtml(h)}</li>`).join("")}
              </ul>
            </div>
          `).join("")}
        </section>
      `;
    } else if (secKey === "CERTIFICATIONS") {
      html += `
        <section class="resume-section">
          <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">CERTIFICATIONS</h3>
          <div class="resume-cert-grid">
            ${(c.certifications || []).map((cert) => `
              <div class="resume-cert-item">
                <strong>${escapeHtml(cert.name)}</strong> — <span>${escapeHtml(cert.issuing_organization)}</span> (${escapeHtml(cert.issue_date || "")})
              </div>
            `).join("")}
          </div>
        </section>
      `;
    } else if (secKey === "PUBLICATIONS") {
      if (c.publications && c.publications.length > 0) {
        html += `
          <section class="resume-section">
            <h3 style="border-bottom: 1.5px solid ${accent}; color: ${accent};">PUBLICATIONS & PATENTS</h3>
            <ul class="resume-bullets">
              ${c.publications.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}
            </ul>
          </section>
        `;
      }
    }
  });

  html += `</div>`;
  canvas.innerHTML = html;
  drawIcons();
}

function updateCustomizerStyles() {
  const canvas = $("#templatePreviewCanvas");
  if (!canvas) return;
  const fs = state.customizer.fontSize || "medium";
  const sp = state.customizer.spacing || "standard";

  canvas.classList.remove("font-compact", "font-standard", "font-spacious");
  canvas.classList.remove("spacing-tight", "spacing-standard", "spacing-relaxed");

  if (fs === "small") canvas.classList.add("font-compact");
  else if (fs === "large") canvas.classList.add("font-spacious");
  else canvas.classList.add("font-standard");

  if (sp === "compact") canvas.classList.add("spacing-tight");
  else if (sp === "relaxed") canvas.classList.add("spacing-relaxed");
  else canvas.classList.add("spacing-standard");
}

function openTemplateCompareModal() {
  const modal = $("#templateCompareModal");
  const container = $("#compareTableContainer");
  if (!modal || !container) return;

  const compareIds = Array.from(state.selectedCompareIds);
  if (compareIds.length === 0) {
    container.innerHTML = `
      <div class="empty-state-card mini">
        <i data-lucide="columns"></i>
        <h4>No templates selected for comparison</h4>
        <p>Tick the <strong>Compare</strong> checkbox on 2 to 4 template cards in the grid to view side-by-side ATS scores, layout orders, and career levels.</p>
      </div>
    `;
    modal.classList.remove("hidden");
    drawIcons();
    return;
  }

  const selectedTemplates = compareIds
    .map((id) => (state.templates || []).find((t) => t.template_id === id))
    .filter(Boolean);

  let tableHtml = `
    <table class="clean-table compare-table">
      <thead>
        <tr>
          <th style="min-width: 160px;">Attribute</th>
          ${selectedTemplates.map((t) => `
            <th style="text-align: center; border-top: 3px solid ${t.accent_color || "#1e3a8a"};">
              <div class="compare-col-header">
                <strong>${escapeHtml(t.name)}</strong>
                <span class="tier-badge ${t.tier === "PRO" ? "pro" : "free"} mt-1">${t.tier}</span>
              </div>
            </th>
          `).join("")}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Category</strong></td>
          ${selectedTemplates.map((t) => `<td style="text-align: center;"><span class="badge-sub">${escapeHtml(t.category)}</span></td>`).join("")}
        </tr>
        <tr>
          <td><strong>ATS Score</strong></td>
          ${selectedTemplates.map((t) => `<td style="text-align: center;"><strong class="text-success">${t.ats_score || 99}% Parsable</strong></td>`).join("")}
        </tr>
        <tr>
          <td><strong>Target Level</strong></td>
          ${selectedTemplates.map((t) => `<td style="text-align: center;" class="text-xs">${(t.best_for_level || []).join(", ") || "All Levels"}</td>`).join("")}
        </tr>
        <tr>
          <td><strong>Recommended Roles</strong></td>
          ${selectedTemplates.map((t) => `<td style="text-align: center;" class="text-xs">${(t.best_for_roles || []).join(", ") || "--"}</td>`).join("")}
        </tr>
        <tr>
          <td><strong>Recommended Pages</strong></td>
          ${selectedTemplates.map((t) => `<td style="text-align: center;" class="text-xs">${t.recommended_length_pages ? t.recommended_length_pages + " page(s)" : "1–2 pages"}</td>`).join("")}
        </tr>
        <tr>
          <td><strong>Section Order</strong></td>
          ${selectedTemplates.map((t) => `<td style="text-align: center;" class="text-xs text-muted">${(t.section_order || []).map(s => capitalize(s.replace(/_/g, " "))).join(" &rarr; ")}</td>`).join("")}
        </tr>
        <tr>
          <td><strong>Action</strong></td>
          ${selectedTemplates.map((t) => `
            <td style="text-align: center;">
              <button class="primary-btn sm w-full" type="button" onclick="selectActiveTemplate('${t.template_id}')">
                <i data-lucide="check"></i><span>Use This</span>
              </button>
            </td>
          `).join("")}
        </tr>
      </tbody>
    </table>
  `;

  container.innerHTML = tableHtml;
  modal.classList.remove("hidden");
  drawIcons();
}

function selectActiveTemplate(templateId) {
  const t = (state.templates || []).find((x) => x.template_id === templateId) || {
    name: capitalize(templateId.replace(/_/g, " ")),
    tier: "FREE",
    description: "",
  };

  const isPro = t.tier === "PRO";
  const userPlan = state.user?.plan_name || "FREE";
  const hasProAccess = userPlan === "PRO_MONTHLY" || userPlan === "PRO_ANNUAL" || userPlan === "PRO_TRIAL";

  if (isPro && !hasProAccess) {
    pendingUpgradeTemplateId = templateId;
    $("#upgradeModalTitle").innerHTML = `<i data-lucide="sparkles"></i> Unlock ${escapeHtml(t.name)}`;
    $("#upgradeModalSubtitle").textContent = `This specialized ${escapeHtml(t.category)} template is included with SmartResume Pro.`;
    $("#upgradeModalDesc").textContent = t.description || "Engineered for maximum recruiter readability and ATS score.";
    $("#templateUpgradeModal")?.classList.remove("hidden");
    drawIcons();
    return;
  }

  state.activeTemplateId = templateId;
  localStorage.setItem("activeTemplateId", templateId);

  syncActiveTemplateDisplay();
  filterAndRenderTemplates();

  // Close modals
  $("#templatePreviewModal")?.classList.add("hidden");
  $("#templateCompareModal")?.classList.add("hidden");
  $("#templateUpgradeModal")?.classList.add("hidden");

  toast(`Activated "${t.name}" as your active resume template!`);
}

function syncActiveTemplateDisplay() {
  const t = (state.templates || []).find((x) => x.template_id === state.activeTemplateId);
  const name = t ? t.name : capitalize(state.activeTemplateId.replace(/_/g, " "));

  // 1. Dashboard active template button
  const dashBtn = $("#dashActiveTemplateName");
  if (dashBtn) dashBtn.textContent = `Template: ${name}`;

  // 2. Application Builder select dropdown
  const selector = $("#templateSelector");
  if (selector && selector.value !== state.activeTemplateId) {
    selector.value = state.activeTemplateId;
  }
}

// ==========================================================================
// 11. GUIDED UX & CONTEXTUAL LEARNING SYSTEM
// ==========================================================================
function wireGuidanceSystem() {
  // 1. Context Guides collapse toggle & dismiss
  $$(".context-guide").forEach((guide) => {
    const guideId = guide.dataset.guideId;
    const isDismissed = localStorage.getItem(`smartresume_dismissed_guide_${guideId}`) === "true";
    if (isDismissed) {
      guide.classList.add("hidden");
    }

    const toggleBtn = guide.querySelector(".toggle-guide-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        guide.classList.toggle("collapsed");
        const icon = toggleBtn.querySelector("i");
        if (icon) {
          icon.setAttribute("data-lucide", guide.classList.contains("collapsed") ? "chevron-down" : "chevron-up");
          drawIcons();
        }
      });
    }

    const dismissBtn = guide.querySelector(".dismiss-guide-btn");
    if (dismissBtn) {
      dismissBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        guide.classList.add("hidden");
        if (guideId) {
          localStorage.setItem(`smartresume_dismissed_guide_${guideId}`, "true");
        }
        toast("Guide dismissed. You can restore tips anytime in Settings.", "info");
      });
    }
  });

  // 2. Settings button to restore all guides
  const resetBtn = $("#resetEducationalGuidesBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      Object.keys(localStorage).forEach((k) => {
        if (k.startsWith("smartresume_dismissed_guide_")) {
          localStorage.removeItem(k);
        }
      });
      $$(".context-guide").forEach((guide) => {
        guide.classList.remove("hidden", "collapsed");
        const icon = guide.querySelector(".toggle-guide-btn i");
        if (icon) icon.setAttribute("data-lucide", "chevron-up");
      });
      drawIcons();
      toast("Educational guides restored across all workspaces!");
    });
  }

  // 3. Term Explainers
  initTermExplainers();
}

const GLOSSARY_TERMS = {
  "evidence": "Verifiable proof (metrics, code repo, project scope, employer record) supporting a resume claim without exaggeration.",
  "readiness": "Deterministic alignment score between verified profile qualifications and target job requirements.",
  "coverage": "Percentage of hard and soft job requirements directly matched by your profile evidence.",
  "strong match": "Direct, verified experience or projects proving exact mastery of the required skill or responsibility.",
  "partial match": "Related, transferable background present, but lacking exact technology or keyword match.",
  "missing evidence": "Requirement mentioned in job posting that has zero supporting proof in your profile.",
  "honest gap": "Requirement intentionally excluded from tailoring because you lack verified evidence, protecting against fabrication.",
  "career level": "Seniority tier (Early Career, Developing Professional, Senior, Lead, Executive) based on verified experience years and scope.",
  "tailoring": "Restructuring existing verified achievements to highlight relevance to a specific role without fabricating unverified claims.",
  "version snapshot": "An immutable, point-in-time copy of your tailored resume locked for export and job submission.",
  "ats health": "Single-column parsability, text-layer integrity, and standard heading hierarchy for machine recruitment scanners.",
};

function initTermExplainers() {
  $$(".term-explain, [data-explain]").forEach((el) => {
    const rawKey = el.dataset.explain || el.textContent.trim().toLowerCase();
    const explanation = GLOSSARY_TERMS[rawKey.toLowerCase()];
    if (explanation) {
      el.setAttribute("title", explanation);
      el.setAttribute("tabindex", "0");
      el.classList.add("has-explainer");
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        toast(`📖 ${capitalize(rawKey)}: ${explanation}`);
      });
    }
  });
}
