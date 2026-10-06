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
  wireResumeBuilder();
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

// Auth state variables (Tokens kept strictly private in memory)
let _activeResetToken = null;
let _activeVerifyToken = null;
let _isAuthSubmitting = false;

const AUTH_ROUTES = {
  "#/signin": "login",
  "#/login": "login",
  "#/register": "register",
  "#/create-account": "register",
  "#/forgot-password": "forgot",
  "#/reset-password": "reset",
  "#/verify-email": "verify",
};

// Boot & Lifecycle
async function boot() {
  document.documentElement.dataset.theme = localStorage.getItem("theme") || "light";

  // Check URL parameters for OAuth, Reset Token, Verify Token, or Auth routes
  const authParam = checkAuthUrlParams();

  if (authParam && authParam.type === "oauth") {
    await handleOAuthCallback(authParam.code, authParam.provider);
    return;
  }

  if (authParam && authParam.type === "reset") {
    showAuth("reset");
    drawIcons();
    return;
  }

  if (authParam && authParam.type === "verify") {
    showAuth("verify");
    drawIcons();
    return;
  }

  if (authParam && authParam.type === "route") {
    showAuth(authParam.mode);
    drawIcons();
    return;
  }

  if (API.getAccessToken()) {
    await loadApp();
  } else {
    showAuth("login");
  }
  drawIcons();
}

function checkAuthUrlParams() {
  const urlParams = new URLSearchParams(window.location.search);
  let hash = window.location.hash || "";
  let hashParams = new URLSearchParams();
  if (hash.includes("?")) {
    const queryPart = hash.substring(hash.indexOf("?") + 1);
    hashParams = new URLSearchParams(queryPart);
  }

  // Token extraction
  const resetToken = urlParams.get("token") || hashParams.get("token") || urlParams.get("reset_token") || hashParams.get("reset_token");
  const verifyToken = urlParams.get("verify_token") || hashParams.get("verify_token") || (hash.includes("verify") ? (urlParams.get("token") || hashParams.get("token")) : null);
  const oauthCode = urlParams.get("code") || hashParams.get("code");
  const stateParam = urlParams.get("state") || hashParams.get("state");
  const storedProvider = typeof sessionStorage !== "undefined" ? sessionStorage.getItem("oauth_provider") : null;
  const scopeParam = urlParams.get("scope") || hashParams.get("scope") || "";

  let oauthProvider = urlParams.get("provider") || hashParams.get("provider");
  if (!oauthProvider) {
    if (stateParam === "google" || storedProvider === "google" || urlParams.has("authuser") || scopeParam.includes("google") || window.location.pathname.includes("google")) {
      oauthProvider = "google";
    } else if (stateParam === "linkedin" || storedProvider === "linkedin" || window.location.pathname.includes("linkedin")) {
      oauthProvider = "linkedin";
    } else {
      oauthProvider = storedProvider || "google";
    }
  }

  if (oauthCode) {
    return { type: "oauth", code: oauthCode, provider: oauthProvider };
  }
  if (resetToken) {
    _activeResetToken = resetToken;
    // Sanitize URL to protect token secrecy
    window.history.replaceState(null, "", window.location.pathname + "#/reset-password");
    return { type: "reset", token: resetToken };
  }
  if (verifyToken) {
    _activeVerifyToken = verifyToken;
    window.history.replaceState(null, "", window.location.pathname + "#/verify-email");
    return { type: "verify", token: verifyToken };
  }

  if (AUTH_ROUTES[hash]) {
    return { type: "route", mode: AUTH_ROUTES[hash] };
  }

  return null;
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

function showAuthAlert(message, type = "error") {
  const alert = $("#authAlert");
  if (!alert) return;
  let safeMessage = message;
  if (typeof safeMessage === "string" && (safeMessage === "Failed to fetch" || safeMessage.includes("Failed to fetch") || safeMessage.includes("NetworkError"))) {
    safeMessage = "Unable to connect to the server. Please ensure the backend is running and reachable.";
  }
  alert.className = `auth-alert ${type}`;
  const iconName = type === "success" ? "check-circle-2" : type === "info" ? "info" : type === "warning" ? "alert-triangle" : "alert-circle";
  alert.innerHTML = `<i data-lucide="${iconName}"></i> <span>${escapeHtml(safeMessage)}</span>`;
  alert.classList.remove("hidden");
  drawIcons();
}

function clearAuthAlert() {
  const alert = $("#authAlert");
  if (alert) {
    alert.className = "auth-alert hidden";
    alert.classList.add("hidden");
    alert.innerHTML = "";
  }
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
  clearAuthAlert();

  const headings = {
    login: "Sign In",
    register: "Create Account",
    forgot: "Forgot Password",
    reset: "Reset Password",
    verify: "Email Verification",
  };
  const subtitles = {
    login: "Welcome back",
    register: "Create your SmartResume account",
    forgot: "Enter your email to receive a secure reset link",
    reset: "Enter a new secure password for your account",
    verify: "Confirming your email address",
  };

  const headingEl = $("#authHeading");
  if (headingEl) headingEl.textContent = headings[mode] || "Sign In";
  const subtitleEl = $("#authSubtitle");
  if (subtitleEl) subtitleEl.textContent = subtitles[mode] || "Welcome back";

  // Hide all forms and state cards first
  ["login", "register", "forgot", "reset"].forEach((name) => {
    const form = $(`#${name}Form`);
    if (form) {
      form.classList.toggle("hidden", name !== mode);
      form.querySelectorAll("input").forEach((inp) => inp.disabled = false);
    }
  });

  const forgotSuccess = $("#forgotSuccessView");
  if (forgotSuccess) forgotSuccess.classList.add("hidden");
  const resetSuccess = $("#resetSuccessView");
  if (resetSuccess) resetSuccess.classList.add("hidden");
  const resetInvalid = $("#resetInvalidView");
  if (resetInvalid) resetInvalid.classList.add("hidden");
  const verifyView = $("#verifyEmailView");
  if (verifyView) verifyView.classList.toggle("hidden", mode !== "verify");

  // Specific state handling for reset mode
  if (mode === "reset") {
    if (!_activeResetToken) {
      const authParam = checkAuthUrlParams();
      if (!authParam || authParam.type !== "reset" || !_activeResetToken) {
        // No token provided in URL or memory! Show invalid link state
        const resetForm = $("#resetForm");
        if (resetForm) resetForm.classList.add("hidden");
        if (resetInvalid) resetInvalid.classList.remove("hidden");
        if (headingEl) headingEl.textContent = "Reset Password";
        if (subtitleEl) subtitleEl.textContent = "Link verification required";
      }
    }
  }

  // Specific state handling for verify mode
  if (mode === "verify") {
    if (_activeVerifyToken) {
      executeEmailVerification(_activeVerifyToken);
    }
  }

  // Footer prompts
  ["login", "register", "forgot", "reset"].forEach((name) => {
    const footer = $(`#authFooter${capitalize(name)}`);
    if (footer) footer.classList.toggle("hidden", name !== mode);
  });

  // OAuth buttons (only on login and register)
  const oauthGroup = $("#oauthActionGroup");
  const oauthDivider = $(".oauth-divider");
  const showOAuth = (mode === "login" || mode === "register");
  if (oauthGroup) oauthGroup.classList.toggle("hidden", !showOAuth);
  if (oauthDivider) oauthDivider.classList.toggle("hidden", !showOAuth);

  // Synchronize URL hash
  const modeToHash = {
    login: "#/signin",
    register: "#/register",
    forgot: "#/forgot-password",
    reset: "#/reset-password",
    verify: "#/verify-email",
  };
  if (modeToHash[mode] && window.location.hash !== modeToHash[mode]) {
    window.history.replaceState(null, "", modeToHash[mode]);
  }

  drawIcons();
}

async function executeEmailVerification(token) {
  const iconWrap = $("#verifyEmailIconWrap");
  const icon = $("#verifyEmailIcon");
  const title = $("#verifyEmailTitle");
  const desc = $("#verifyEmailDescription");
  const actionBtn = $("#verifyEmailActionBtn");

  if (title) title.textContent = "Verifying email...";
  if (desc) desc.textContent = "Please wait while we verify your email address...";

  try {
    await API.request("/auth/verify-email", {
      method: "POST",
      auth: false,
      body: { token },
    });
    _activeVerifyToken = null;
    if (iconWrap) iconWrap.className = "state-card-icon success";
    if (icon) icon.setAttribute("data-lucide", "check-circle-2");
    if (title) title.textContent = "Email verified";
    if (desc) desc.textContent = "Your email address has been verified successfully. You can now access your account.";
    if (actionBtn) actionBtn.classList.remove("hidden");
    drawIcons();
  } catch (error) {
    _activeVerifyToken = null;
    if (iconWrap) iconWrap.className = "state-card-icon warning";
    if (icon) icon.setAttribute("data-lucide", "alert-triangle");
    if (title) title.textContent = "Verification failed";
    if (desc) desc.textContent = error.message || "This verification link is invalid or has expired.";
    drawIcons();
  }
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

function wirePasswordToggles() {
  $$(".password-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.toggleTarget;
      const input = document.getElementById(targetId);
      if (!input) return;
      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
      btn.setAttribute("title", isPassword ? "Hide password" : "Show password");
      btn.innerHTML = `<i data-lucide="${isPassword ? "eye-off" : "eye"}"></i>`;
      drawIcons();
    });
  });
}

function evaluatePasswordRequirements(password, prefix = "req", meterId = "registerStrengthMeter") {
  const hasLen = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasCase = hasUpper && hasLower;
  const hasNum = /\d/.test(password);
  const hasSym = /[^A-Za-z0-9]/.test(password);

  const reqs = [
    { el: $(`#${prefix}Len`), met: hasLen },
    { el: $(`#${prefix}Case`), met: hasCase },
    { el: $(`#${prefix}Num`), met: hasNum },
    { el: $(`#${prefix}Sym`), met: hasSym },
  ];

  let metCount = 0;
  reqs.forEach(({ el, met }) => {
    if (!el) return;
    el.classList.toggle("met", met);
    const icon = el.querySelector("i, svg");
    if (icon) {
      el.innerHTML = `<i data-lucide="${met ? "check-circle-2" : "circle"}"></i> ${el.textContent.trim()}`;
    }
    if (met) metCount++;
  });

  const meter = $(`#${meterId}`);
  if (meter) {
    const percent = (metCount / 4) * 100;
    meter.style.width = `${percent}%`;
    if (metCount === 0) {
      meter.style.width = "0%";
    } else if (metCount <= 1) {
      meter.style.backgroundColor = "var(--danger)";
    } else if (metCount === 2) {
      meter.style.backgroundColor = "var(--warning)";
    } else if (metCount === 3) {
      meter.style.backgroundColor = "#3b82f6";
    } else {
      meter.style.backgroundColor = "var(--success)";
    }
  }

  drawIcons();
  return metCount === 4;
}

function checkConfirmPasswordMatch(passwordId, confirmId, feedbackId) {
  const pw = $(`#${passwordId}`)?.value || "";
  const cpw = $(`#${confirmId}`)?.value || "";
  const feedback = $(`#${feedbackId}`);
  if (!feedback) return true;

  if (!cpw) {
    feedback.classList.add("hidden");
    feedback.textContent = "";
    return true;
  }

  feedback.classList.remove("hidden");
  if (pw === cpw) {
    feedback.className = "field-feedback success";
    feedback.innerHTML = '<i data-lucide="check"></i> Passwords match';
    drawIcons();
    return true;
  } else {
    feedback.className = "field-feedback error";
    feedback.innerHTML = '<i data-lucide="alert-circle"></i> Passwords do not match';
    drawIcons();
    return false;
  }
}

// AUTHENTICATION & SOCIAL OAUTH 2.0
function wireAuth() {
  wirePasswordToggles();

  // Contextual auth links
  $$("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
  });

  // Clear alerts on input
  $$("#authView input").forEach((input) => {
    input.addEventListener("input", () => clearAuthAlert());
  });

  // Progressive password validation on Register
  const regPw = $("#registerPassword");
  if (regPw) {
    regPw.addEventListener("input", (e) => {
      evaluatePasswordRequirements(e.target.value, "req", "registerStrengthMeter");
      checkConfirmPasswordMatch("registerPassword", "registerConfirmPassword", "registerMismatchHint");
    });
  }
  const regCpw = $("#registerConfirmPassword");
  if (regCpw) {
    regCpw.addEventListener("input", () => {
      checkConfirmPasswordMatch("registerPassword", "registerConfirmPassword", "registerMismatchHint");
    });
  }

  // Progressive password validation on Reset
  const resPw = $("#resetPassword");
  if (resPw) {
    resPw.addEventListener("input", (e) => {
      evaluatePasswordRequirements(e.target.value, "resetReq", "resetStrengthMeter");
      checkConfirmPasswordMatch("resetPassword", "resetConfirmPassword", "resetMismatchHint");
    });
  }
  const resCpw = $("#resetConfirmPassword");
  if (resCpw) {
    resCpw.addEventListener("input", () => {
      checkConfirmPasswordMatch("resetPassword", "resetConfirmPassword", "resetMismatchHint");
    });
  }

  // Google OAuth button
  const googleBtn = $("#googleOAuthBtn");
  if (googleBtn) {
    googleBtn.addEventListener("click", async () => {
      try {
        clearAuthAlert();
        if (typeof sessionStorage !== "undefined") {
          sessionStorage.setItem("oauth_provider", "google");
        }
        const config = await API.request("/auth/oauth/config", { auth: false });
        state.oauthConfig = config;
        if (config.google?.configured || config.google_enabled) {
          const urlData = await API.request("/auth/oauth/google/url", { auth: false });
          window.location.href = urlData.url;
        } else {
          openOAuthModal("Google Sign-In", "Google 1-click sign-in is currently unavailable in this environment. Please sign in with your email address.");
        }
      } catch (err) {
        openOAuthModal("Google Sign-In", "Google sign-in is currently unavailable. Please continue with your email address.");
      }
    });
  }

  // LinkedIn OAuth button
  const linkedinBtn = $("#linkedinOAuthBtn");
  if (linkedinBtn) {
    linkedinBtn.addEventListener("click", async () => {
      try {
        clearAuthAlert();
        if (typeof sessionStorage !== "undefined") {
          sessionStorage.setItem("oauth_provider", "linkedin");
        }
        const config = await API.request("/auth/oauth/config", { auth: false });
        state.oauthConfig = config;
        if (config.linkedin?.configured || config.linkedin_enabled) {
          const urlData = await API.request("/auth/oauth/linkedin/url", { auth: false });
          window.location.href = urlData.url;
        } else {
          openOAuthModal("LinkedIn Sign-In", "LinkedIn 1-click sign-in is currently unavailable in this environment. Please sign in with your email address.");
        }
      } catch (err) {
        openOAuthModal("LinkedIn Sign-In", "LinkedIn sign-in is currently unavailable. Please continue with your email address.");
      }
    });
  }

  // OAuth Modal close buttons
  const closeOAuthBtn = $("#closeOAuthModalBtn");
  if (closeOAuthBtn) {
    closeOAuthBtn.addEventListener("click", () => $("#oauthModal")?.classList.add("hidden"));
  }
  const dismissOAuthBtn = $("#dismissOAuthModalBtn");
  if (dismissOAuthBtn) {
    dismissOAuthBtn.addEventListener("click", () => $("#oauthModal")?.classList.add("hidden"));
  }

  // Standard Email Login
  const loginForm = $("#loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (_isAuthSubmitting) return;

      const email = $("#loginEmail").value.trim();
      const password = $("#loginPassword").value;

      if (!email || !password) {
        showAuthAlert("Please enter both your email address and password.");
        return;
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        showAuthAlert("Please enter a valid email address.");
        return;
      }

      const btn = loginForm.querySelector("button[type='submit']");
      _isAuthSubmitting = true;
      setButtonLoading(btn, true, "Signing in...");
      loginForm.querySelectorAll("input").forEach((inp) => inp.disabled = true);
      clearAuthAlert();

      try {
        const data = await API.request("/auth/login", {
          method: "POST",
          auth: false,
          body: { email, password },
        });
        API.setSession(data);
        toast("Welcome back!");
        await loadApp();
      } catch (error) {
        showAuthAlert(error.message || "Incorrect email or password. Please try again.");
      } finally {
        _isAuthSubmitting = false;
        setButtonLoading(btn, false, "Sign In");
        loginForm.querySelectorAll("input").forEach((inp) => inp.disabled = false);
      }
    });
  }

  // Register Form
  const registerForm = $("#registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (_isAuthSubmitting) return;

      const fullName = $("#registerName").value.trim();
      const email = $("#registerEmail").value.trim();
      const password = $("#registerPassword").value;
      const confirmPassword = $("#registerConfirmPassword").value;

      if (!fullName) {
        showAuthAlert("Please enter your full name.");
        return;
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!email || !emailRegex.test(email)) {
        showAuthAlert("Please enter a valid email address.");
        return;
      }

      if (!evaluatePasswordRequirements(password, "req", "registerStrengthMeter")) {
        showAuthAlert("Password must meet all 4 security requirements.");
        return;
      }

      if (password !== confirmPassword) {
        showAuthAlert("Passwords do not match. Please verify your password.");
        return;
      }

      const btn = registerForm.querySelector("button[type='submit']");
      _isAuthSubmitting = true;
      setButtonLoading(btn, true, "Creating account...");
      registerForm.querySelectorAll("input").forEach((inp) => inp.disabled = true);
      clearAuthAlert();

      try {
        await API.request("/auth/register", {
          method: "POST",
          auth: false,
          body: {
            full_name: fullName,
            email: email,
            password: password,
          },
        });
        toast("Account created successfully!");
        setAuthMode("login");
        $("#loginEmail").value = email;
        showAuthAlert("Account created successfully! Please sign in with your credentials.", "success");
      } catch (error) {
        showAuthAlert(error.message || "Unable to create account. Please check your information.");
      } finally {
        _isAuthSubmitting = false;
        setButtonLoading(btn, false, "Create Account");
        registerForm.querySelectorAll("input").forEach((inp) => inp.disabled = false);
      }
    });
  }

  // Forgot Password
  const forgotForm = $("#forgotForm");
  if (forgotForm) {
    forgotForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (_isAuthSubmitting) return;

      const email = $("#forgotEmail").value.trim();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!email || !emailRegex.test(email)) {
        showAuthAlert("Please enter a valid email address.");
        return;
      }

      const btn = forgotForm.querySelector("button[type='submit']");
      _isAuthSubmitting = true;
      setButtonLoading(btn, true, "Sending reset link...");
      forgotForm.querySelectorAll("input").forEach((inp) => inp.disabled = true);
      clearAuthAlert();

      try {
        await API.request("/auth/forgot-password", {
          method: "POST",
          auth: false,
          body: { email },
        });

        // Show clean success card
        forgotForm.classList.add("hidden");
        const successCard = $("#forgotSuccessView");
        if (successCard) {
          const emailDisplay = $("#forgotSentEmail");
          if (emailDisplay) emailDisplay.textContent = email;
          successCard.classList.remove("hidden");
        }
        const heading = $("#authHeading");
        if (heading) heading.textContent = "Check Your Email";
        const subtitle = $("#authSubtitle");
        if (subtitle) subtitle.textContent = "Password reset instructions sent";
        drawIcons();
      } catch (error) {
        showAuthAlert(error.message || "Unable to send reset instructions. Please try again.");
      } finally {
        _isAuthSubmitting = false;
        setButtonLoading(btn, false, "Send Reset Link");
        forgotForm.querySelectorAll("input").forEach((inp) => inp.disabled = false);
      }
    });
  }

  // Reset Password (Token read silently in memory, never exposed as form field)
  const resetForm = $("#resetForm");
  if (resetForm) {
    resetForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (_isAuthSubmitting) return;

      if (!_activeResetToken) {
        showAuthAlert("Password reset token is missing. Please request a new link.");
        setAuthMode("reset");
        return;
      }

      const newPassword = $("#resetPassword").value;
      const confirmNewPassword = $("#resetConfirmPassword").value;

      if (!evaluatePasswordRequirements(newPassword, "resetReq", "resetStrengthMeter")) {
        showAuthAlert("Password must meet all 4 security requirements.");
        return;
      }

      if (newPassword !== confirmNewPassword) {
        showAuthAlert("Passwords do not match. Please verify your new password.");
        return;
      }

      const btn = resetForm.querySelector("button[type='submit']");
      _isAuthSubmitting = true;
      setButtonLoading(btn, true, "Resetting password...");
      resetForm.querySelectorAll("input").forEach((inp) => inp.disabled = true);
      clearAuthAlert();

      try {
        await API.request("/auth/reset-password", {
          method: "POST",
          auth: false,
          body: { token: _activeResetToken, new_password: newPassword },
        });

        _activeResetToken = null; // Clean from memory
        resetForm.classList.add("hidden");
        const successCard = $("#resetSuccessView");
        if (successCard) successCard.classList.remove("hidden");
        const heading = $("#authHeading");
        if (heading) heading.textContent = "Password Updated";
        const subtitle = $("#authSubtitle");
        if (subtitle) subtitle.textContent = "You can now sign in with your new password";
        drawIcons();
      } catch (error) {
        _activeResetToken = null;
        resetForm.classList.add("hidden");
        const invalidCard = $("#resetInvalidView");
        if (invalidCard) {
          const p = invalidCard.querySelector("p");
          if (p) p.textContent = error.message || "This password reset link is no longer valid or has expired.";
          invalidCard.classList.remove("hidden");
        }
        drawIcons();
      } finally {
        _isAuthSubmitting = false;
        setButtonLoading(btn, false, "Reset Password");
        resetForm.querySelectorAll("input").forEach((inp) => inp.disabled = false);
      }
    });
  }

  // Logout
  const logoutBtn = $("#logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await API.request("/auth/logout", {
          method: "POST",
          body: { refresh_token: API.getRefreshToken() },
        });
      } catch (_) {}
      API.clearSession();
      showAuth("login");
    });
  }
}

function openOAuthModal(title, message) {
  const modalTitle = $("#oauthModalTitle");
  if (modalTitle) modalTitle.innerHTML = `<i data-lucide="key"></i> ${escapeHtml(title)}`;
  const modalMsg = $("#oauthModalMessage");
  if (modalMsg) modalMsg.textContent = message;
  const modal = $("#oauthModal");
  if (modal) modal.classList.remove("hidden");
  drawIcons();
}

async function handleOAuthCallback(code, provider) {
  clearAuthAlert();
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.removeItem("oauth_provider");
  }
  toast(`Authenticating with ${capitalize(provider)}...`);
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
    toast(`Authentication failed: ${error.message}`, "error");
    window.history.replaceState({}, document.title, window.location.pathname);
    showAuth("login");
  }
}

const ROUTES = {
  "#/dashboard": "dashboard",
  "#/career-profile": "profile",
  "#/profile": "profile",
  "#/evidence": "evidence-vault",
  "#/evidence-vault": "evidence-vault",
  "#/resume-builder": "resume-builder",
  "#/templates": "templates",
  "#/job-radar": "job-radar",
  "#/job-match": "fit",
  "#/check-job-fit": "fit",
  "#/fit": "fit",
  "#/application-builder": "tailor",
  "#/prepare-application": "tailor",
  "#/tailor": "tailor",
  "#/smartapply": "smartapply",
  "#/applications": "applications",
  "#/application-tracker": "applications",
  "#/interview": "interview",
  "#/insights": "career-insights",
  "#/career-insights": "career-insights",
  "#/billing": "billing",
  "#/settings": "settings",
};

const TAB_TO_ROUTE = {
  "dashboard": "#/dashboard",
  "profile": "#/profile",
  "evidence-vault": "#/evidence",
  "resume-builder": "#/resume-builder",
  "templates": "#/templates",
  "job-radar": "#/job-radar",
  "fit": "#/check-job-fit",
  "tailor": "#/prepare-application",
  "smartapply": "#/smartapply",
  "applications": "#/application-tracker",
  "interview": "#/interview",
  "career-insights": "#/insights",
  "insights": "#/insights",
  "billing": "#/billing",
  "settings": "#/settings",
};

const TAB_MAP = {
  "dashboard": "tabDashboard",
  "profile": "tabProfile",
  "evidence-vault": "tabEvidenceVault",
  "resume-builder": "tabResumeBuilder",
  "templates": "tabTemplates",
  "job-radar": "tabJobRadar",
  "fit": "tabFit",
  "tailor": "tabApplicationBuilder",
  "smartapply": "tabSmartApply",
  "applications": "tabApplications",
  "interview": "tabInterview",
  "career-insights": "tabCareerInsights",
  "insights": "tabCareerInsights",
  "billing": "tabBilling",
  "settings": "tabSettings",
};

function wireNavigation() {
  function activateTab(tabName, updateHash = true) {
    const validTab = TAB_MAP[tabName] ? tabName : "dashboard";

    // 1. Highlight sidebar & mobile navigation items (map sub-tabs to their parent journey pillar)
    const TAB_PARENT_MAP = {
      "evidence-vault": "profile",
      "templates": "resume-builder",
      "job-radar": "fit",
      "tailor": "applications",
      "smartapply": "applications",
      "career-insights": "interview",
      "insights": "interview",
    };
    const primaryNavTab = TAB_PARENT_MAP[validTab] || validTab;

    $$(".nav-tabs button, .nav-groups .nav-item, .mobile-bottom-nav .mobile-nav-item").forEach((item) => {
      if (item.dataset.tab === primaryNavTab) {
        item.classList.add("active");
        item.setAttribute("aria-selected", "true");
        const label = item.querySelector("span") ? item.querySelector("span").textContent.trim() : item.textContent.trim();
        const pageTitleEl = $("#pageTitle");
        if (pageTitleEl && label && label !== "Menu") pageTitleEl.textContent = label;
        document.title = `SmartResume.ai — ${label}`;
      } else {
        item.classList.remove("active");
        item.setAttribute("aria-selected", "false");
      }
    });

    // Highlight active sub-navigation pills across all workspace headers
    $$(".subnav-pill").forEach((pill) => {
      const onclickAttr = pill.getAttribute("onclick") || "";
      if (onclickAttr.includes(`'${validTab}'`) || onclickAttr.includes(`"${validTab}"`)) {
        pill.classList.add("active");
      } else {
        pill.classList.remove("active");
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
    if (validTab === "resume-builder") loadResumeBuilderView();
    if (validTab === "templates") loadTemplatesView();
    if (validTab === "evidence-vault") loadEvidenceVault();
    if (validTab === "job-radar") loadJobRadar();
    if (validTab === "career-insights") loadCareerInsights();
    if (validTab === "interview") {
      loadInterviewSessions();
      loadClaimsToDefend();
      syncInterviewContextUI();
    } else {
      stopLiveInterviewMedia();
    }
    if (validTab === "smartapply") loadSmartApplyAnswers();
    if (validTab === "billing") {
      loadBillingSummary();
      loadPaymentHistory();
    }
    if (validTab === "dashboard") renderDashboard();

    drawIcons();
  }

  // Navigation button click events
  $$(".nav-tabs button, .nav-groups .nav-item, .mobile-bottom-nav .mobile-nav-item[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      activateTab(button.dataset.tab, true);
    });
  });

  // Browser Back / Forward hash navigation
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash;
    if (AUTH_ROUTES[hash]) {
      showAuth(AUTH_ROUTES[hash]);
      return;
    }
    const tabName = ROUTES[hash] || "dashboard";
    activateTab(tabName, false);
  });

  // Mobile drawer controls
  const mobileMenuBtn = $("#mobileMenuBtn");
  const mobileMoreNavBtn = $("#mobileMoreNavBtn");
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
  if (mobileMoreNavBtn) mobileMoreNavBtn.addEventListener("click", openMobileDrawer);
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

  // 1. User Greeting
  const firstName = (state.user?.name || p.full_name || "Job Seeker").trim().split(" ")[0];
  const welcomeEl = $("#dashWelcomeName");
  if (welcomeEl) welcomeEl.textContent = firstName;

  // 2. Prominent Current Resume Hero Card vs No Resume State
  const hasProfileData = !!(p.full_name || (p.experiences && p.experiences.length > 0) || (p.skills && p.skills.length > 0));
  const heroCard = $("#dashCurrentResumeHeroCard");
  const noResumeCard = $("#dashNoResumeHeroCard");
  if (heroCard && noResumeCard) {
    heroCard.classList.toggle("hidden", !hasProfileData);
    noResumeCard.classList.toggle("hidden", hasProfileData);
  }

  // Active Template name & badge
  const resumeNameEl = $("#dashCurrentResumeName");
  const resumeBadgeEl = $("#dashCurrentResumeBadge");
  const activeTplId = state.activeTemplateId || state.activeTemplate || "classic_ats";
  const tplDef = (state.templates || []).find(t => t.template_id === activeTplId) || (window.RESUME_TEMPLATES || []).find(t => t.id === activeTplId) || { name: "Classic ATS", isPro: false };

  if (resumeNameEl) {
    resumeNameEl.textContent = tplDef.name || "Classic ATS";
  }
  if (resumeBadgeEl) {
    const isUserPro = state.user?.plan === "PRO" || state.user?.is_pro;
    const isTrial = state.user?.is_trial;
    if (tplDef.isPro && !isUserPro && !isTrial) {
      resumeBadgeEl.textContent = "PRO 🔒";
      resumeBadgeEl.className = "badge-sub badge-pro-lock";
    } else if (tplDef.isPro && isTrial) {
      resumeBadgeEl.textContent = "PRO · Trial included";
      resumeBadgeEl.className = "badge-sub badge-pro-trial";
    } else if (tplDef.isPro) {
      resumeBadgeEl.textContent = "PRO";
      resumeBadgeEl.className = "badge-sub badge-pro";
    } else {
      resumeBadgeEl.textContent = "Standard";
      resumeBadgeEl.className = "badge-sub";
    }
  }

  // 3. Dynamic Next Best Action Calculation
  computeAndRenderNextBestAction(hasProfileData, score);

  // 4. Career Profile Readiness Meter
  const completenessEl = $("#dashCompletenessPercent");
  if (completenessEl) completenessEl.textContent = `${score}%`;
  const circle = $("#dashMeterCircle");
  if (circle) {
    if (score >= 80) {
      circle.style.borderColor = "var(--success)";
      const lbl = $("#dashCompletenessLabel");
      if (lbl) lbl.textContent = "Strong Profile Grounding";
    } else if (score >= 50) {
      circle.style.borderColor = "var(--warning)";
      const lbl = $("#dashCompletenessLabel");
      if (lbl) lbl.textContent = "Moderate Profile Strength";
    } else {
      circle.style.borderColor = "var(--primary)";
      const lbl = $("#dashCompletenessLabel");
      if (lbl) lbl.textContent = "Foundation In Progress";
    }
  }

  // Profile readiness tip
  const tipEl = $("#dashReadinessTip");
  if (tipEl) {
    if (score < 50) {
      tipEl.textContent = "Add your recent work experience and 3 top skills to build your career foundation.";
    } else if (score < 80) {
      tipEl.textContent = "Add key projects or certifications to reach 80% and improve recruiter readability.";
    } else {
      tipEl.textContent = "Your profile is well-grounded! Tailor your resume for specific roles to stand out.";
    }
  }

  // Hidden compatibility elements
  const q1 = $("#dashQ1Answer");
  if (q1) q1.textContent = score >= 80 ? "Strong evidence across core skills." : "Foundation in progress.";
  const q2 = $("#dashQ2Answer");
  if (q2) q2.textContent = state.jobs?.length ? `${state.jobs.length} jobs matched` : "";
  const q3 = $("#dashQ3Answer");
  if (q3) q3.textContent = "Keep profile updated.";
  const q4 = $("#dashQ4Answer");
  if (q4) q4.textContent = state.applications?.length ? `${state.applications.length} applications tracked` : "";

  // Quotas in Dashboard (if present)
  if (state.quotas) {
    const q = state.quotas.quotas || {};
    const fits = q.fit_analyses || { used: 0, limit: 2 };
    const tailors = q.tailored_versions || { used: 0, limit: 2 };
    const exports_ = q.exports || { used: 0, limit: 2 };

    if ($("#dashFitsUsage")) $("#dashFitsUsage").textContent = `${fits.used} / ${fits.limit}`;
    if ($("#dashFitsBar")) $("#dashFitsBar").style.width = `${Math.min(100, Math.round((fits.used / (fits.limit || 1)) * 100))}%`;

    if ($("#dashTailorsUsage")) $("#dashTailorsUsage").textContent = `${tailors.used} / ${tailors.limit}`;
    if ($("#dashTailorsBar")) $("#dashTailorsBar").style.width = `${Math.min(100, Math.round((tailors.used / (tailors.limit || 1)) * 100))}%`;

    if ($("#dashExportsUsage")) $("#dashExportsUsage").textContent = `${exports_.used} / ${exports_.limit}`;
    if ($("#dashExportsBar")) $("#dashExportsBar").style.width = `${Math.min(100, Math.round((exports_.used / (exports_.limit || 1)) * 100))}%`;
  }

  // 5. Recent Applications on Dashboard
  const appContainer = $("#dashApplicationsList");
  if (appContainer) {
    appContainer.innerHTML = "";
    if (!state.applications || state.applications.length === 0) {
      appContainer.innerHTML = `
        <div class="empty-state-structured" style="padding: 24px 16px;">
          <div class="empty-icon"><i data-lucide="briefcase"></i></div>
          <h4 style="font-size: 0.95rem;">No job applications tracked yet</h4>
          <p style="font-size: 0.8rem; margin-bottom: 12px;">Track your submissions and interview stages in one organized pipeline.</p>
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
  }

  // 6. Recent Activity Stream on Dashboard
  const actContainer = $("#dashRecentActivityList");
  if (actContainer) {
    actContainer.innerHTML = "";
    const activities = [];
    if (state.applications && state.applications.length > 0) {
      state.applications.slice(0, 2).forEach((app) => {
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
      state.jobs.slice(0, 2).forEach((job) => {
        activities.push({
          icon: "crosshair",
          title: `Job Match: ${job.title} at ${job.company}`,
          subtitle: `Calibrated with keyword analysis`,
          date: job.created_at ? new Date(job.created_at).toLocaleDateString() : "Recent",
          actionTab: "fit",
        });
      });
    }
    if (state.profile?.updated_at) {
      activities.push({
        icon: "user-check",
        title: "Career Profile Updated",
        subtitle: `Profile strength: ${score}%`,
        date: new Date(state.profile.updated_at).toLocaleDateString(),
        actionTab: "profile",
      });
    }

    if (activities.length === 0) {
      actContainer.innerHTML = `
        <div class="empty-state-structured" style="padding: 24px 16px;">
          <div class="empty-icon"><i data-lucide="activity"></i></div>
          <h4 style="font-size: 0.95rem;">No recent activity</h4>
          <p style="font-size: 0.8rem; margin-bottom: 0;">Match a job or polish your resume to see your activity timeline.</p>
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

function computeAndRenderNextBestAction(hasProfileData, score) {
  const iconEl = $("#dashNextActionIcon");
  const titleEl = $("#dashNextActionTitle");
  const descEl = $("#dashNextActionDesc");
  const btnEl = $("#dashNextActionBtn");
  const btnTextEl = $("#dashNextActionBtnText");

  if (!titleEl || !btnEl) return;

  if (!hasProfileData) {
    if (iconEl) iconEl.setAttribute("data-lucide", "file-plus");
    titleEl.textContent = "Create your first resume";
    if (descEl) descEl.textContent = "Start with our guided builder to generate an ATS-ready resume in minutes.";
    if (btnTextEl) btnTextEl.textContent = "Create My Resume";
    btnEl.onclick = () => {
      const modal = $("#onboardingModal");
      if (modal) {
        modal.classList.remove("hidden");
        resetOnboardingWizard();
      } else {
        navigateToTab("resume-builder");
      }
    };
  } else if (!state.jobs || state.jobs.length === 0) {
    if (iconEl) iconEl.setAttribute("data-lucide", "crosshair");
    titleEl.textContent = "Match your resume to a target job";
    if (descEl) descEl.textContent = "Paste any job posting to see how well you qualify and what keywords recruiters expect.";
    if (btnTextEl) btnTextEl.textContent = "Match a Target Job";
    btnEl.onclick = () => navigateToTab("fit");
  } else if (!state.applications || state.applications.length === 0) {
    const topJob = state.jobs[0];
    if (iconEl) iconEl.setAttribute("data-lucide", "sparkles");
    titleEl.textContent = `Prepare application for ${topJob.title}`;
    if (descEl) descEl.textContent = `Tailor your resume bullets specifically for ${topJob.company} to maximize your interview chances.`;
    if (btnTextEl) btnTextEl.textContent = "Prepare Job Application";
    btnEl.onclick = () => navigateToTab("tailor");
  } else {
    const topApp = state.applications[0];
    if (iconEl) iconEl.setAttribute("data-lucide", "messages-square");
    titleEl.textContent = `Prepare for your interview at ${topApp.company}`;
    if (descEl) descEl.textContent = `Practice realistic mock interview questions tailored to the ${topApp.job_title} role.`;
    if (btnTextEl) btnTextEl.textContent = "Practice Interview";
    btnEl.onclick = () => navigateToTab("interview");
  }
}

function openActiveResumePreview() {
  const tplId = state.activeTemplateId || "classic_ats";
  if (typeof openTemplatePreview === "function") {
    openTemplatePreview(tplId);
  } else if (typeof openTemplatePreviewModal === "function") {
    openTemplatePreviewModal(tplId);
  } else {
    navigateToTab("resume-builder");
  }
}
window.openActiveResumePreview = openActiveResumePreview;
window.openTemplatePreviewModal = openActiveResumePreview;

// ==========================================================================
// RESUME BUILDER CONTROLLER (Two-column interactive editor + live canvas)
// ==========================================================================

const DEFAULT_SECTION_TITLES = {
  summary: "Professional Summary",
  skills: "Skills",
  experiences: "Work Experience",
  projects: "Key Projects",
  education: "Education",
  certifications: "Certifications",
  achievements: "Achievements & Awards",
  awards: "Awards & Honors",
  languages: "Languages",
  volunteer: "Volunteer Experience",
  leadership: "Leadership & Activities",
  publications: "Publications",
  courses: "Relevant Coursework"
};

let resumeBuilderState = {
  template: "classic_ats",
  fontSize: "medium",
  spacing: "standard",
  accentColor: "#1e3a8a",
  dateFormat: "MMM YYYY",
  skillsLayout: "inline", // "inline" or "grouped"
  sectionOrder: ["summary", "skills", "experiences", "projects", "education", "certifications", "achievements", "languages"],
  sectionTitles: Object.assign({}, DEFAULT_SECTION_TITLES),
  header: {
    full_name: "",
    headline: "",
    email: "",
    phone: "",
    location: "",
    linkedin: "",
    github: "",
    website: ""
  },
  summary: "",
  skills: [],
  skillCategories: [],
  experiences: [],
  projects: [],
  education: [],
  certifications: [],
  achievements: [],
  awards: [],
  languages: [],
  volunteer: [],
  leadership: [],
  publications: [],
  courses: [],
  customSections: []
};

let builderAutosaveTimeout = null;

function sanitizeHtmlForPreview(rawHtml) {
  if (!rawHtml || typeof rawHtml !== "string") return "";
  const allowed = new Set(["B", "STRONG", "I", "EM", "U", "A", "UL", "OL", "LI", "P", "SPAN", "BR"]);
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(rawHtml, "text/html");
    function cleanNode(node) {
      const children = Array.from(node.childNodes);
      for (const child of children) {
        if (child.nodeType === Node.ELEMENT_NODE) {
          if (!allowed.has(child.tagName)) {
            const text = document.createTextNode(child.textContent || "");
            node.replaceChild(text, child);
          } else {
            const attrs = Array.from(child.attributes);
            for (const attr of attrs) {
              if (child.tagName === "A" && (attr.name === "href" || attr.name === "target" || attr.name === "rel")) {
                if (attr.name === "href" && !/^(https?:\/\/|mailto:|tel:)/i.test(attr.value)) {
                  child.removeAttribute(attr.name);
                }
              } else {
                child.removeAttribute(attr.name);
              }
            }
            if (child.tagName === "A") {
              child.setAttribute("target", "_blank");
              child.setAttribute("rel", "noopener noreferrer");
            }
            cleanNode(child);
          }
        }
      }
    }
    cleanNode(doc.body);
    return doc.body.innerHTML;
  } catch (e) {
    return escapeHtml(rawHtml);
  }
}

function formatDateStrClient(dateStr, fmt = "MMM YYYY") {
  if (!dateStr || typeof dateStr !== "string") return "";
  const s = dateStr.trim();
  if (!s) return "";
  if (/^(present|current|now)$/i.test(s)) return "Present";
  if (/^\d{4}$/.test(s)) return s;

  const monthNamesShort = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const monthNamesFull = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  let year = null;
  let month = null;

  let m = s.match(/^(\d{4})[-\/.](\d{1,2})$/);
  if (m) {
    year = parseInt(m[1], 10);
    month = parseInt(m[2], 10);
  }
  if (!year) {
    m = s.match(/^(\d{1,2})[-\/.](\d{4})$/);
    if (m) {
      month = parseInt(m[1], 10);
      year = parseInt(m[2], 10);
    }
  }
  if (!year) {
    m = s.match(/^([a-zA-Z]+)[,\s]+(\d{4})$/);
    if (m) {
      year = parseInt(m[2], 10);
      const mStr = m[1].toLowerCase();
      const idx = monthNamesShort.findIndex(n => n.toLowerCase() === mStr.slice(0, 3));
      if (idx !== -1) month = idx + 1;
    }
  }

  if (year && month && month >= 1 && month <= 12) {
    const mm = String(month).padStart(2, "0");
    const mShort = monthNamesShort[month - 1];
    const mFull = monthNamesFull[month - 1];

    if (fmt === "MM/YYYY") return `${mm}/${year}`;
    if (fmt === "MMMM YYYY") return `${mFull} ${year}`;
    if (fmt === "YYYY") return String(year);
    return `${mShort} ${year}`;
  }

  return s;
}

function formatClientDateRange(startDate, endDate, isCurrent, fmt = "MMM YYYY") {
  const s = formatDateStrClient(startDate, fmt);
  const e = isCurrent ? "Present" : formatDateStrClient(endDate, fmt);
  if (s && e) return `${s} – ${e}`;
  if (s) return s;
  if (e) return e;
  return "";
}

function cleanBulletHtml(html) {
  if (!html) return [];
  const str = html
    .replace(/<br\s*[\/]?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/div>/gi, "\n")
    .replace(/<\/li>/gi, "\n")
    .replace(/<[!\/]?[a-z0-9]+[^>]*>/gi, (match) => {
      const tag = match.toLowerCase();
      if (/^<\/?(b|i|u|strong|em|a)(\s|>)/.test(tag)) {
        return match;
      }
      return "";
    });

  return str.split("\n")
    .map(line => line.replace(/^[\s•\-\*]+/, "").trim())
    .filter(Boolean);
}

function renderRichToolbar(editorId) {
  return `
    <div class="rich-text-toolbar" data-for="${editorId}">
      <button type="button" class="rich-toolbar-btn" data-command="bold" title="Bold (Ctrl+B)"><b>B</b></button>
      <button type="button" class="rich-toolbar-btn" data-command="italic" title="Italic (Ctrl+I)"><i>I</i></button>
      <button type="button" class="rich-toolbar-btn" data-command="underline" title="Underline (Ctrl+U)"><u>U</u></button>
      <span class="rich-toolbar-sep"></span>
      <button type="button" class="rich-toolbar-btn" data-command="insertUnorderedList" title="Bullet List">• list</button>
      <button type="button" class="rich-toolbar-btn" data-command="createLink" title="Insert Link">🔗</button>
      <button type="button" class="rich-toolbar-btn" data-command="removeFormat" title="Clear Formatting">Tx</button>
    </div>
  `;
}

function getCleanResumeBuilderState() {
  const p = state.profile || {};
  const u = state.user || {};

  return {
    template: state.activeTemplateId || "classic_ats",
    fontSize: state.customizer?.fontSize || "medium",
    spacing: state.customizer?.spacing || "standard",
    accentColor: state.customizer?.accentColor || "#1e3a8a",
    dateFormat: "MMM YYYY",
    skillsLayout: "inline",
    sectionOrder: ["summary", "skills", "experiences", "projects", "education", "certifications", "achievements", "languages"],
    sectionTitles: Object.assign({}, DEFAULT_SECTION_TITLES),
    header: {
      full_name: p.full_name || u.full_name || "",
      headline: p.headline || "",
      email: p.email || u.email || "",
      phone: p.phone || "",
      location: p.location || "",
      linkedin: p.linkedin_url || "",
      github: p.github_url || "",
      website: p.website_url || ""
    },
    summary: p.summary || "",
    skills: (p.skills || []).map(s => typeof s === "string" ? s : s.name).filter(Boolean),
    skillCategories: [],
    experiences: (p.experiences || []).map(e => ({
      title: e.title || e.role_title || "",
      company: e.company || "",
      location: e.location || "",
      start_date: e.start_date || "",
      end_date: e.end_date || "",
      is_current: !!e.is_current,
      bullets: (e.bullets || e.bullet_points || []).map(b => typeof b === "string" ? b : (b.text || "")),
      is_hidden: false
    })),
    projects: (p.projects || []).map(pr => ({
      title: pr.title || pr.name || "",
      technologies: Array.isArray(pr.technologies) ? pr.technologies.join(", ") : (pr.technologies || ""),
      url: pr.url || pr.repo_url || "",
      start_date: pr.start_date || "",
      end_date: pr.end_date || "",
      description: pr.description || "",
      bullets: (pr.bullets || pr.bullet_points || []).map(b => typeof b === "string" ? b : (b.text || "")),
      is_hidden: false
    })),
    education: (p.education || []).map(ed => ({
      institution: ed.institution || "",
      degree: ed.degree || "",
      field_of_study: ed.field_of_study || "",
      start_date: ed.start_date || "",
      end_date: ed.end_date || ed.graduation_year || "",
      grade: ed.grade || ed.gpa || "",
      location: ed.location || "",
      is_hidden: false
    })),
    certifications: (p.certifications || []).map(c => ({
      name: typeof c === "string" ? c : (c.name || ""),
      issuer: typeof c === "object" ? (c.issuer || "") : "",
      date: typeof c === "object" ? (c.issue_date || c.date || "") : "",
      is_hidden: false
    })),
    achievements: [],
    awards: [],
    languages: (p.languages || []).map(l => ({
      language: typeof l === "string" ? l : (l.language || l.name || ""),
      proficiency: typeof l === "object" ? (l.proficiency || "Proficient") : "Proficient",
      is_hidden: false
    })),
    volunteer: [],
    leadership: [],
    publications: [],
    courses: [],
    customSections: []
  };
}

function loadResumeBuilderState() {
  try {
    const raw = localStorage.getItem("smartresume_builder_state");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && parsed.header) {
        const clean = getCleanResumeBuilderState();
        resumeBuilderState = Object.assign(clean, parsed);
        resumeBuilderState.sectionTitles = Object.assign({}, DEFAULT_SECTION_TITLES, parsed.sectionTitles || {});
        if (resumeBuilderState.sectionTitles.skills === "Skills & Technologies") {
          resumeBuilderState.sectionTitles.skills = "Skills";
        }
        if (!Array.isArray(resumeBuilderState.sectionOrder)) {
          resumeBuilderState.sectionOrder = clean.sectionOrder;
        }
        if (!resumeBuilderState.dateFormat) resumeBuilderState.dateFormat = "MMM YYYY";
        if (!resumeBuilderState.skillsLayout) resumeBuilderState.skillsLayout = "inline";
        if (!Array.isArray(resumeBuilderState.skillCategories)) resumeBuilderState.skillCategories = [];
        if (!Array.isArray(resumeBuilderState.customSections)) resumeBuilderState.customSections = [];
        return;
      }
    }
  } catch (e) {
    console.warn("Failed to load builder state from storage", e);
  }
  resumeBuilderState = getCleanResumeBuilderState();
}

function triggerBuilderAutosave() {
  const statusEl = $("#builderSaveStatus");
  if (statusEl) {
    statusEl.className = "builder-save-status saving";
    statusEl.innerHTML = '<span class="status-dot"></span><span>Saving...</span>';
  }
  if (builderAutosaveTimeout) clearTimeout(builderAutosaveTimeout);
  builderAutosaveTimeout = setTimeout(() => {
    try {
      localStorage.setItem("smartresume_builder_state", JSON.stringify(resumeBuilderState));
      if (statusEl) {
        statusEl.className = "builder-save-status";
        statusEl.innerHTML = '<span class="status-dot"></span><span>Saved</span>';
      }
    } catch (e) {
      if (statusEl) {
        statusEl.className = "builder-save-status";
        statusEl.innerHTML = '<span class="status-dot" style="background:#ef4444;"></span><span>Local save error</span>';
      }
    }
  }, 400);
}

function wireResumeBuilder() {
  // Sync profile button
  $("#builderSyncProfileBtn")?.addEventListener("click", () => {
    if (confirm("Sync will refresh your resume fields with the latest data from your Career Profile. Continue?")) {
      resumeBuilderState = getCleanResumeBuilderState();
      triggerBuilderAutosave();
      renderBuilderEditorFromState();
      renderResumePreviewCanvas();
      toast("Synchronized with your Career Profile.");
    }
  });

  // Template select
  $("#builderTemplateSelect")?.addEventListener("change", (e) => {
    resumeBuilderState.template = e.target.value;
    state.activeTemplateId = e.target.value;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  });

  // Font size
  $("#builderFontSize")?.addEventListener("change", (e) => {
    resumeBuilderState.fontSize = e.target.value;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  });

  // Spacing
  $("#builderSpacing")?.addEventListener("change", (e) => {
    resumeBuilderState.spacing = e.target.value;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  });

  // Accent Color
  $("#builderAccentColor")?.addEventListener("input", (e) => {
    resumeBuilderState.accentColor = e.target.value;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  });

  // Date Format Select
  $("#builderDateFormat")?.addEventListener("change", (e) => {
    resumeBuilderState.dateFormat = e.target.value;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  });

  // Add Section Select
  const addSecSelect = $("#builderAddSectionSelect");
  if (addSecSelect) {
    addSecSelect.addEventListener("change", (e) => {
      const val = e.target.value;
      if (!val) return;
      if (val === "custom_new") {
        const title = prompt("Enter title for Custom Section (e.g. Patents, Exhibitions, Client Engagements):", "Custom Section");
        if (title && title.trim()) {
          const customId = "custom_" + Date.now();
          if (!resumeBuilderState.customSections) resumeBuilderState.customSections = [];
          resumeBuilderState.customSections.push({
            id: customId,
            title: title.trim(),
            items: []
          });
          if (!resumeBuilderState.sectionTitles) resumeBuilderState.sectionTitles = {};
          resumeBuilderState.sectionTitles[customId] = title.trim();
          resumeBuilderState.sectionOrder.push(customId);
          triggerBuilderAutosave();
          renderBuilderEditorFromState();
          renderResumePreviewCanvas();
          toast(`Added custom section "${title.trim()}".`);
        }
      } else {
        if (!resumeBuilderState.sectionOrder.includes(val)) {
          resumeBuilderState.sectionOrder.push(val);
        }
        if (!resumeBuilderState[val] && ["volunteer", "leadership", "publications", "courses", "experiences", "projects", "education", "certifications", "achievements", "awards", "languages"].includes(val)) {
          resumeBuilderState[val] = [];
        }
        triggerBuilderAutosave();
        renderBuilderEditorFromState();
        renderResumePreviewCanvas();
        const displayTitle = (resumeBuilderState.sectionTitles && resumeBuilderState.sectionTitles[val]) || DEFAULT_SECTION_TITLES[val] || val;
        toast(`Added ${displayTitle} section to resume.`);
      }
      e.target.value = "";
    });
  }

  // Header input bindings
  const headerKeys = [
    { id: "builderFullName", key: "full_name" },
    { id: "builderHeadline", key: "headline" },
    { id: "builderEmail", key: "email" },
    { id: "builderPhone", key: "phone" },
    { id: "builderLocation", key: "location" },
    { id: "builderLinkedin", key: "linkedin" },
    { id: "builderGithub", key: "github" },
    { id: "builderWebsite", key: "website" },
  ];
  headerKeys.forEach(({ id, key }) => {
    const el = $(`#${id}`);
    if (el) {
      el.addEventListener("input", (e) => {
        resumeBuilderState.header[key] = e.target.value;
        triggerBuilderAutosave();
        renderResumePreviewCanvas();
      });
    }
  });

  // Fullscreen preview
  $("#builderFullscreenPreviewBtn")?.addEventListener("click", () => {
    openActiveResumePreview();
  });

  // Export buttons in Resume Builder
  $("#builderDownloadPdfBtn")?.addEventListener("click", () => {
    executeResumeBuilderExport("pdf");
  });

  $("#builderDownloadDocxBtn")?.addEventListener("click", () => {
    executeResumeBuilderExport("docx");
  });

  // Score Modal Button in Builder
  $("#builderCheckScoreBtn")?.addEventListener("click", () => {
    openResumeScoreModal();
  });

  // Recalculate Button in Score Modal
  $("#scoreRecalculateBtn")?.addEventListener("click", () => {
    runResumeScoreCalculation();
  });

  // Global Rich Text keyboard shortcuts (Ctrl+B, Ctrl+I, Ctrl+U)
  if (!window._richTextShortcutsWired) {
    window._richTextShortcutsWired = true;
    document.addEventListener("keydown", (e) => {
      const editable = e.target.closest('.rich-text-content[contenteditable="true"]');
      if (!editable) return;
      if (e.ctrlKey || e.metaKey) {
        const k = e.key.toLowerCase();
        if (k === "b") {
          e.preventDefault();
          document.execCommand("bold", false, null);
          editable.dispatchEvent(new Event("input", { bubbles: true }));
        } else if (k === "i") {
          e.preventDefault();
          document.execCommand("italic", false, null);
          editable.dispatchEvent(new Event("input", { bubbles: true }));
        } else if (k === "u") {
          e.preventDefault();
          document.execCommand("underline", false, null);
          editable.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }
    });

    document.addEventListener("mousedown", (e) => {
      const btn = e.target.closest(".rich-toolbar-btn");
      if (!btn) return;
      e.preventDefault();
      const wrapper = btn.closest(".rich-text-wrapper");
      const content = wrapper ? wrapper.querySelector('.rich-text-content[contenteditable="true"]') : null;
      if (!content) return;
      content.focus();
      const cmd = btn.dataset.command;
      if (cmd === "createLink") {
        const url = prompt("Enter link URL (e.g. https://...):");
        if (url) document.execCommand("createLink", false, url);
      } else {
        document.execCommand(cmd, false, null);
      }
      content.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }
}

let lastResumeScore = null;

async function openResumeScoreModal(targetRole, careerLevel) {
  const modal = $("#resumeScoreModal");
  if (!modal) return;
  modal.classList.remove("hidden");

  if (targetRole && $("#scoreTargetRoleInput")) {
    $("#scoreTargetRoleInput").value = targetRole;
  }
  if (careerLevel && $("#scoreCareerLevelSelect")) {
    $("#scoreCareerLevelSelect").value = careerLevel;
  }

  await runResumeScoreCalculation();
}
window.openResumeScoreModal = openResumeScoreModal;

async function runResumeScoreCalculation() {
  const targetRole = $("#scoreTargetRoleInput")?.value.trim() || "Software Engineer";
  const careerLevel = $("#scoreCareerLevelSelect")?.value || "EARLY_CAREER";

  // Gather current resume data
  const resumeData = Object.assign({}, resumeBuilderState);

  try {
    toast("Calculating evidence-based resume score...");
    const res = await API.request("/resumes/score", {
      method: "POST",
      body: {
        resume_data: resumeData,
        target_role: targetRole,
        career_level: careerLevel,
        previous_score: lastResumeScore,
      },
    });

    lastResumeScore = res.overall_score;
    renderResumeScoreModal(res);
  } catch (err) {
    toast(err.message || "Failed to calculate resume score", "error");
  }
}
window.runResumeScoreCalculation = runResumeScoreCalculation;

function renderResumeScoreModal(data) {
  if (!data) return;

  // 1. Overall Score & styling
  const scoreNum = $("#scoreModalNum");
  if (scoreNum) {
    scoreNum.textContent = data.overall_score;
    if (data.overall_score >= 80) {
      scoreNum.style.color = "#10b981";
    } else if (data.overall_score >= 60) {
      scoreNum.style.color = "#f59e0b";
    } else {
      scoreNum.style.color = "#ef4444";
    }
  }

  // 2. Target role
  const targetText = $("#scoreHeroTargetText");
  if (targetText) {
    targetText.textContent = `${data.target_role || "Role"} Evaluation`;
  }

  // 3. Fresher calibrated badge
  const calBadge = $("#scoreFresherCalibratedBadge");
  if (calBadge) {
    if (data.is_fresher_calibrated) {
      calBadge.classList.remove("hidden");
      calBadge.textContent = "Fresher Calibrated · Experience Penalty Waived";
    } else {
      calBadge.textContent = "Professional Evaluation";
    }
  }

  // 4. Delta pill and explanation
  const deltaPill = $("#scoreDeltaPill");
  const deltaExp = $("#scoreDeltaExplanation");
  if (data.score_delta !== null && data.score_delta !== undefined) {
    if (deltaPill) {
      deltaPill.classList.remove("hidden");
      const sign = data.score_delta > 0 ? `+${data.score_delta}` : `${data.score_delta}`;
      deltaPill.textContent = `${sign} vs previous`;
      deltaPill.style.color = data.score_delta >= 0 ? "#10b981" : "#ef4444";
    }
    if (deltaExp) {
      deltaExp.textContent = data.delta_explanation || "";
    }
  } else {
    if (deltaPill) deltaPill.classList.add("hidden");
    if (deltaExp) deltaExp.textContent = "";
  }

  // 5. What is Helping
  const helpList = $("#scoreHelpingList");
  if (helpList) {
    helpList.innerHTML = (data.what_is_helping || []).map((item) => `
      <li>
        <i data-lucide="check" style="color: #10b981; width: 14px; height: 14px; flex-shrink: 0; margin-top: 2px;"></i>
        <span>${escapeHtml(item)}</span>
      </li>
    `).join("");
  }

  // 6. What is Holding Back
  const holdList = $("#scoreHoldingBackList");
  if (holdList) {
    holdList.innerHTML = (data.what_is_holding_back || []).map((item) => `
      <li>
        <i data-lucide="alert-triangle" style="color: #f59e0b; width: 14px; height: 14px; flex-shrink: 0; margin-top: 2px;"></i>
        <span>${escapeHtml(item)}</span>
      </li>
    `).join("");
  }

  // 7. Top Priority Improvements
  const impList = $("#scoreTopImprovementsList");
  if (impList) {
    if (data.top_improvements && data.top_improvements.length > 0) {
      impList.innerHTML = data.top_improvements.map((imp) => {
        const priority = imp.priority || imp.impact || "MEDIUM";
        const impactClass = priority.toLowerCase();
        const title = imp.problem || imp.title || "Improvement";
        const explanation = imp.why || imp.explanation || "";
        const action = imp.action || imp.suggested_action || "";
        let exHtml = "";
        if (imp.example) {
          exHtml = `
            <div class="mt-2 p-2 bg-surface border rounded text-xs">
              <span class="text-muted font-bold">Concrete Fix:</span>
              <div class="font-mono text-xs mt-1" style="white-space: pre-wrap;">${escapeHtml(imp.example)}</div>
            </div>
          `;
        }
        return `
          <div class="priority-fix-card ${impactClass}">
            <div class="flex-between align-center mb-1">
              <strong>${escapeHtml(title)}</strong>
              <span class="priority-tag ${impactClass}">${escapeHtml(priority)} IMPACT</span>
            </div>
            <p class="text-xs text-muted mb-1">${escapeHtml(explanation)}</p>
            <p class="text-xs font-semibold mb-0" style="color: var(--primary);">${escapeHtml(action)}</p>
            ${exHtml}
          </div>
        `;
      }).join("");
    } else {
      impList.innerHTML = `<p class="text-xs text-muted">No high priority fixes needed! Your resume has strong evidence alignment.</p>`;
    }
  }

  // 8. Dimensions
  const dimsList = $("#scoreDimensionsList");
  if (dimsList) {
    const dimEntries = Array.isArray(data.dimensions)
      ? data.dimensions
      : Object.values(data.dimensions || {});
    dimsList.innerHTML = dimEntries.map((d) => {
      const weightDisplay = typeof d.weight === "number" ? `${Math.round(d.weight * 100)}% weight` : (d.weight || "");
      return `
        <div class="dim-row">
          <div class="dim-label-row">
            <span class="font-semibold text-xs">${escapeHtml(d.name || "Dimension")}</span>
            <span class="text-xs font-bold">${d.score}/100 <span class="text-muted font-normal">(${weightDisplay})</span></span>
          </div>
          <div class="dim-bar">
            <div class="dim-fill" style="width: ${d.score}%;"></div>
          </div>
          <span class="text-xs text-muted mt-1 block">${escapeHtml(d.explanation || "")}</span>
        </div>
      `;
    }).join("");
  }

  // 9. Buzzwords
  const buzzSec = $("#scoreBuzzwordsSection");
  const buzzList = $("#scoreBuzzwordsList");
  if (buzzSec && buzzList) {
    if (data.buzzwords_detected && data.buzzwords_detected.length > 0) {
      buzzSec.classList.remove("hidden");
      buzzList.innerHTML = data.buzzwords_detected.map((b) => `
        <div class="buzzword-chip">
          <strong>"${escapeHtml(b.phrase)}"</strong>: ${escapeHtml(b.suggestion || b.reason)}
        </div>
      `).join("");
    } else {
      buzzSec.classList.add("hidden");
    }
  }

  // 10. Eligibility Gaps
  const eligSec = $("#scoreEligibilityGapsSection");
  const eligText = $("#scoreEligibilityGapsText");
  if (eligSec && eligText) {
    if (data.eligibility_gaps && data.eligibility_gaps.length > 0) {
      eligSec.classList.remove("hidden");
      eligText.textContent = data.eligibility_gaps.join("; ");
    } else {
      eligSec.classList.add("hidden");
    }
  }

  drawIcons();
}

async function executeResumeBuilderExport(format = "pdf") {
  const btn = format === "pdf" ? $("#builderDownloadPdfBtn") : $("#builderDownloadDocxBtn");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader" class="spin"></i><span>Generating ${format.toUpperCase()}...</span>`;
    drawIcons();
  }

  try {
    toast(`Preparing your ${format.toUpperCase()} resume...`);
    const token = API.getAccessToken();

    const h = resumeBuilderState.header || {};
    const payload = {
      format,
      template_name: resumeBuilderState.template || "classic_ats",
      accent_color: resumeBuilderState.accentColor || "#1e3a8a",
      font_size: resumeBuilderState.fontSize || "medium",
      spacing: resumeBuilderState.spacing || "standard",
      date_format: resumeBuilderState.dateFormat || "MMM YYYY",
      section_order: resumeBuilderState.sectionOrder || ["summary", "skills", "experiences", "projects", "education", "certifications", "achievements", "languages"],
      section_titles: resumeBuilderState.sectionTitles || {},
      content: {
        candidate_name: h.full_name || state.user?.full_name || "Resume",
        headline: h.headline || "",
        summary: resumeBuilderState.summary || "",
        email: h.email || state.user?.email || "",
        phone: h.phone || "",
        location: h.location || "",
        linkedin_url: h.linkedin || "",
        github_url: h.github || "",
        website_url: h.website || "",
        skills_layout: resumeBuilderState.skillsLayout || "inline",
        skill_categories: resumeBuilderState.skillCategories || [],
        skills: resumeBuilderState.skills || [],
        experiences: (resumeBuilderState.experiences || []).map(e => ({
          role_title: e.title || "",
          company: e.company || "",
          location: e.location || "",
          start_date: e.start_date || "",
          end_date: e.end_date || "",
          is_current: !!e.is_current,
          bullet_points: e.bullets || [],
          is_hidden: !!e.is_hidden
        })),
        projects: (resumeBuilderState.projects || []).map(p => ({
          title: p.title || "",
          technologies: typeof p.technologies === "string" ? p.technologies.split(",").map(t => t.trim()).filter(Boolean) : (p.technologies || []),
          url: p.url || "",
          start_date: p.start_date || "",
          end_date: p.end_date || "",
          description: p.description || "",
          bullet_points: p.bullets || [],
          is_hidden: !!p.is_hidden
        })),
        education: (resumeBuilderState.education || []).map(ed => ({
          institution: ed.institution || "",
          degree: ed.degree || "",
          field_of_study: ed.field_of_study || "",
          start_date: ed.start_date || "",
          end_date: ed.end_date || "",
          gpa: ed.grade || "",
          location: ed.location || "",
          is_hidden: !!ed.is_hidden
        })),
        certifications: (resumeBuilderState.certifications || []).map(c => ({
          name: c.name || "",
          issuer: c.issuer || "",
          issue_date: c.date || "",
          is_hidden: !!c.is_hidden
        })),
        achievements: (resumeBuilderState.achievements || []).map(a => typeof a === "string" ? { text: a, is_hidden: false } : a),
        awards: (resumeBuilderState.awards || []).map(aw => typeof aw === "string" ? { text: aw, is_hidden: false } : aw),
        languages: (resumeBuilderState.languages || []).map(l => ({
          language: l.language || "",
          proficiency: l.proficiency || "",
          is_hidden: !!l.is_hidden
        })),
        volunteer: (resumeBuilderState.volunteer || []).map(v => ({
          role: v.role || "",
          organization: v.organization || "",
          location: v.location || "",
          start_date: v.start_date || "",
          end_date: v.end_date || "",
          is_current: !!v.is_current,
          description: v.description || "",
          bullet_points: v.bullets || [],
          is_hidden: !!v.is_hidden
        })),
        leadership: (resumeBuilderState.leadership || []).map(l => ({
          role: l.role || "",
          organization: l.organization || "",
          location: l.location || "",
          start_date: l.start_date || "",
          end_date: l.end_date || "",
          description: l.description || "",
          bullet_points: l.bullets || [],
          is_hidden: !!l.is_hidden
        })),
        publications: (resumeBuilderState.publications || []).map(pb => ({
          title: pb.title || "",
          publisher: pb.publisher || "",
          date: pb.date || "",
          url: pb.url || "",
          description: pb.description || "",
          is_hidden: !!pb.is_hidden
        })),
        courses: (resumeBuilderState.courses || []).map(cs => ({
          name: cs.name || "",
          institution: cs.institution || "",
          date: cs.date || "",
          is_hidden: !!cs.is_hidden
        })),
        custom_sections: resumeBuilderState.customSections || [],
        section_titles: resumeBuilderState.sectionTitles || {}
      }
    };

    const res = await fetch("/api/v1/resumes/export-profile", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Server returned error ${res.status}`);
    }

    const blob = await res.blob();
    const rawName = (payload.content.candidate_name || "Resume").trim();
    const safeName = rawName.replace(/[^\w\-]/g, "_");
    const filename = `${safeName}_Resume.${format}`;

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    toast(`${format.toUpperCase()} downloaded successfully!`);
  } catch (err) {
    toast(`Export failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
      drawIcons();
    }
  }
}

function openActiveResumePreview() {
  const modal = $("#resumeFullscreenModal");
  const container = $("#fullscreenCanvasContainer");
  const canvas = $("#builderPreviewCanvas");
  if (!modal || !container || !canvas) return;

  container.innerHTML = "";
  const clone = canvas.closest(".resume-preview-sheet").cloneNode(true);
  clone.id = "fullscreenSheetClone";
  clone.style.boxShadow = "0 8px 30px rgba(0, 0, 0, 0.15)";
  container.appendChild(clone);

  const dlPdfBtn = $("#fullscreenDownloadPdfBtn");
  if (dlPdfBtn) {
    dlPdfBtn.onclick = () => executeResumeBuilderExport("pdf");
  }

  modal.classList.remove("hidden");
  drawIcons();
}

function loadResumeBuilderView() {
  loadResumeBuilderState();

  // Sync toolbar selects to loaded state
  const tplSelect = $("#builderTemplateSelect");
  if (tplSelect && resumeBuilderState.template) tplSelect.value = resumeBuilderState.template;

  const fontSelect = $("#builderFontSize");
  if (fontSelect && resumeBuilderState.fontSize) fontSelect.value = resumeBuilderState.fontSize;

  const spacingSelect = $("#builderSpacing");
  if (spacingSelect && resumeBuilderState.spacing) spacingSelect.value = resumeBuilderState.spacing;

  const accentInput = $("#builderAccentColor");
  if (accentInput && resumeBuilderState.accentColor) accentInput.value = resumeBuilderState.accentColor;

  const dateFmtSelect = $("#builderDateFormat");
  if (dateFmtSelect && resumeBuilderState.dateFormat) dateFmtSelect.value = resumeBuilderState.dateFormat;

  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
}

// Section management helpers
window.moveBuilderSection = function(secKey, dir) {
  const idx = resumeBuilderState.sectionOrder.indexOf(secKey);
  if (idx === -1) return;
  const targetIdx = idx + dir;
  if (targetIdx < 0 || targetIdx >= resumeBuilderState.sectionOrder.length) return;
  const temp = resumeBuilderState.sectionOrder[idx];
  resumeBuilderState.sectionOrder[idx] = resumeBuilderState.sectionOrder[targetIdx];
  resumeBuilderState.sectionOrder[targetIdx] = temp;
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.updateBuilderSectionTitle = function(secKey, title) {
  if (!resumeBuilderState.sectionTitles) resumeBuilderState.sectionTitles = {};
  resumeBuilderState.sectionTitles[secKey] = title.trim();
  if (secKey.startsWith("custom_")) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === secKey);
    if (cs) cs.title = title.trim();
  }
  triggerBuilderAutosave();
  renderResumePreviewCanvas();
};

window.removeBuilderSection = function(secKey) {
  const idx = resumeBuilderState.sectionOrder.indexOf(secKey);
  if (idx !== -1) {
    resumeBuilderState.sectionOrder.splice(idx, 1);
    triggerBuilderAutosave();
    renderBuilderEditorFromState();
    renderResumePreviewCanvas();
    toast("Section removed from resume.");
  }
};

// Repeatable entry controls
window.addBuilderEntry = function(collection, customId) {
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs) {
      if (!Array.isArray(cs.items)) cs.items = [];
      cs.items.push({ title: "", subtitle: "", date: "", description: "", bullets: [""], is_hidden: false });
    }
  } else if (collection === "experiences") {
    resumeBuilderState.experiences.push({ title: "", company: "", location: "", start_date: "", end_date: "", is_current: false, bullets: [""], is_hidden: false });
  } else if (collection === "projects") {
    resumeBuilderState.projects.push({ title: "", technologies: "", url: "", start_date: "", end_date: "", description: "", bullets: [""], is_hidden: false });
  } else if (collection === "education") {
    resumeBuilderState.education.push({ institution: "", degree: "", field_of_study: "", start_date: "", end_date: "", grade: "", location: "", is_hidden: false });
  } else if (collection === "certifications") {
    resumeBuilderState.certifications.push({ name: "", issuer: "", date: "", is_hidden: false });
  } else if (collection === "achievements") {
    resumeBuilderState.achievements.push({ text: "", is_hidden: false });
  } else if (collection === "awards") {
    if (!resumeBuilderState.awards) resumeBuilderState.awards = [];
    resumeBuilderState.awards.push({ text: "", is_hidden: false });
  } else if (collection === "languages") {
    resumeBuilderState.languages.push({ language: "", proficiency: "Proficient", is_hidden: false });
  } else if (collection === "volunteer") {
    if (!resumeBuilderState.volunteer) resumeBuilderState.volunteer = [];
    resumeBuilderState.volunteer.push({ role: "", organization: "", location: "", start_date: "", end_date: "", is_current: false, description: "", bullets: [""], is_hidden: false });
  } else if (collection === "leadership") {
    if (!resumeBuilderState.leadership) resumeBuilderState.leadership = [];
    resumeBuilderState.leadership.push({ role: "", organization: "", location: "", start_date: "", end_date: "", description: "", bullets: [""], is_hidden: false });
  } else if (collection === "publications") {
    if (!resumeBuilderState.publications) resumeBuilderState.publications = [];
    resumeBuilderState.publications.push({ title: "", publisher: "", date: "", url: "", description: "", is_hidden: false });
  } else if (collection === "courses") {
    if (!resumeBuilderState.courses) resumeBuilderState.courses = [];
    resumeBuilderState.courses.push({ name: "", institution: "", date: "", is_hidden: false });
  }
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.removeBuilderItem = function(collection, idx, customId) {
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs && cs.items) cs.items.splice(idx, 1);
  } else if (resumeBuilderState[collection]) {
    resumeBuilderState[collection].splice(idx, 1);
  }
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.moveBuilderEntry = function(collection, idx, dir, customId) {
  let list = null;
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs) list = cs.items;
  } else {
    list = resumeBuilderState[collection];
  }
  if (!list || idx < 0 || idx >= list.length) return;
  const target = idx + dir;
  if (target < 0 || target >= list.length) return;
  const temp = list[idx];
  list[idx] = list[target];
  list[target] = temp;
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.duplicateBuilderEntry = function(collection, idx, customId) {
  let list = null;
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs) list = cs.items;
  } else {
    list = resumeBuilderState[collection];
  }
  if (!list || idx < 0 || idx >= list.length) return;
  const copy = JSON.parse(JSON.stringify(list[idx]));
  list.splice(idx + 1, 0, copy);
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
  toast("Entry duplicated.");
};

window.toggleBuilderEntryVisibility = function(collection, idx, isHidden, customId) {
  let list = null;
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs) list = cs.items;
  } else {
    list = resumeBuilderState[collection];
  }
  if (!list || !list[idx]) return;
  if (typeof list[idx] === "object") {
    list[idx].is_hidden = !!isHidden;
  } else {
    list[idx] = { text: String(list[idx]), is_hidden: !!isHidden };
  }
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.updateBuilderItemField = function(collection, idx, field, val, customId) {
  let item = null;
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs && cs.items) item = cs.items[idx];
  } else if (resumeBuilderState[collection]) {
    item = resumeBuilderState[collection][idx];
  }
  if (item) {
    item[field] = val;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  }
};

window.updateBuilderItemBullets = function(collection, idx, htmlVal, customId) {
  let item = null;
  if (collection === "custom" && customId) {
    const cs = (resumeBuilderState.customSections || []).find(c => c.id === customId);
    if (cs && cs.items) item = cs.items[idx];
  } else if (resumeBuilderState[collection]) {
    item = resumeBuilderState[collection][idx];
  }
  if (item) {
    item.bullets = cleanBulletHtml(htmlVal);
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  }
};

window.updateBuilderAchievement = function(idx, val) {
  if (resumeBuilderState.achievements) {
    if (typeof resumeBuilderState.achievements[idx] === "object") {
      resumeBuilderState.achievements[idx].text = val;
    } else {
      resumeBuilderState.achievements[idx] = { text: val, is_hidden: false };
    }
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  }
};

window.updateBuilderAward = function(idx, val) {
  if (!resumeBuilderState.awards) resumeBuilderState.awards = [];
  if (typeof resumeBuilderState.awards[idx] === "object") {
    resumeBuilderState.awards[idx].text = val;
  } else {
    resumeBuilderState.awards[idx] = { text: val, is_hidden: false };
  }
  triggerBuilderAutosave();
  renderResumePreviewCanvas();
};

// Skills Layout & Categories
window.setSkillsLayout = function(layout) {
  resumeBuilderState.skillsLayout = layout;
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.updateSkillsInline = function(val) {
  resumeBuilderState.skills = val.split(",").map(s => s.trim()).filter(Boolean);
  triggerBuilderAutosave();
  renderResumePreviewCanvas();
};

window.addSkillCategory = function() {
  if (!resumeBuilderState.skillCategories) resumeBuilderState.skillCategories = [];
  resumeBuilderState.skillCategories.push({ name: "Core Skills", skills: [] });
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

window.updateSkillCategoryName = function(catIdx, name) {
  if (resumeBuilderState.skillCategories && resumeBuilderState.skillCategories[catIdx]) {
    resumeBuilderState.skillCategories[catIdx].name = name;
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  }
};

window.updateSkillCategorySkills = function(catIdx, val) {
  if (resumeBuilderState.skillCategories && resumeBuilderState.skillCategories[catIdx]) {
    resumeBuilderState.skillCategories[catIdx].skills = val.split(",").map(s => s.trim()).filter(Boolean);
    triggerBuilderAutosave();
    renderResumePreviewCanvas();
  }
};

window.removeSkillCategory = function(catIdx) {
  if (resumeBuilderState.skillCategories) {
    resumeBuilderState.skillCategories.splice(catIdx, 1);
    triggerBuilderAutosave();
    renderBuilderEditorFromState();
    renderResumePreviewCanvas();
  }
};

window.moveSkillCategory = function(catIdx, dir) {
  const cats = resumeBuilderState.skillCategories;
  if (!cats || catIdx < 0 || catIdx >= cats.length) return;
  const target = catIdx + dir;
  if (target < 0 || target >= cats.length) return;
  const temp = cats[catIdx];
  cats[catIdx] = cats[target];
  cats[target] = temp;
  triggerBuilderAutosave();
  renderBuilderEditorFromState();
  renderResumePreviewCanvas();
};

function renderBuilderEditorFromState() {
  const h = resumeBuilderState.header || {};
  const setVal = (id, val) => { const el = $(`#${id}`); if (el) el.value = val || ""; };

  setVal("builderFullName", h.full_name);
  setVal("builderHeadline", h.headline);
  setVal("builderEmail", h.email);
  setVal("builderPhone", h.phone);
  setVal("builderLocation", h.location);
  setVal("builderLinkedin", h.linkedin);
  setVal("builderGithub", h.github);
  setVal("builderWebsite", h.website);

  const container = $("#builderDynamicSectionsList");
  if (!container) return;

  const sectionOrder = resumeBuilderState.sectionOrder || ["summary", "skills", "experiences", "projects", "education", "certifications", "achievements", "languages"];

  container.innerHTML = sectionOrder.map((secKey, secIdx) => {
    const isFirst = secIdx === 0;
    const isLast = secIdx === sectionOrder.length - 1;
    const secTitle = (resumeBuilderState.sectionTitles && resumeBuilderState.sectionTitles[secKey]) || DEFAULT_SECTION_TITLES[secKey] || "Section";

    let icon = "file-text";
    let addBtnHtml = "";
    let bodyHtml = "";

    if (secKey === "summary") {
      icon = "align-left";
      const sumVal = resumeBuilderState.summary || "";
      bodyHtml = `
        <div class="rich-text-wrapper mb-2">
          ${renderRichToolbar("builderSummaryContent")}
          <div class="rich-text-content" id="builderSummaryContent" contenteditable="true"
               data-placeholder="Brief 2-4 sentence overview of your domain expertise, quantifiable achievements, and core specializations..."
               oninput="resumeBuilderState.summary = this.innerHTML; $('#builderSummaryCharCount').textContent = (this.textContent || '').length + ' characters'; triggerBuilderAutosave(); renderResumePreviewCanvas();">${sanitizeHtmlForPreview(sumVal)}</div>
        </div>
        <div class="flex-row justify-end">
          <span class="text-xs text-muted" id="builderSummaryCharCount">${sumVal.replace(/<[^>]+>/g, "").length} characters</span>
        </div>
      `;
    } else if (secKey === "skills") {
      icon = "award";
      const isGrouped = resumeBuilderState.skillsLayout === "grouped";
      const inlineSkillsStr = (resumeBuilderState.skills || []).join(", ");
      const categories = resumeBuilderState.skillCategories || [];

      bodyHtml = `
        <div class="column-stack gap-3">
          <div class="flex-row align-center justify-between p-2 rounded bg-surface border">
            <span class="text-xs font-semibold">Skills Presentation:</span>
            <div class="flex-row align-center gap-2">
              <label class="flex-row align-center gap-1 text-xs" style="cursor: pointer;">
                <input type="radio" name="skillsLayoutRadio" value="inline" ${!isGrouped ? "checked" : ""} onchange="setSkillsLayout('inline')">
                <span>Standard Inline (Comma-separated)</span>
              </label>
              <label class="flex-row align-center gap-1 text-xs" style="cursor: pointer;">
                <input type="radio" name="skillsLayoutRadio" value="grouped" ${isGrouped ? "checked" : ""} onchange="setSkillsLayout('grouped')">
                <span>Grouped by Category</span>
              </label>
            </div>
          </div>

          ${!isGrouped ? `
            <div>
              <label class="text-xs text-muted mb-1 block">Enter all skills separated by commas:</label>
              <textarea rows="3" placeholder="e.g. Strategic Planning, Team Leadership, Budgeting, Financial Analysis, Process Optimization"
                        oninput="updateSkillsInline(this.value)">${escapeHtml(inlineSkillsStr)}</textarea>
              <div class="text-xs text-muted mt-1">Skills will render cleanly as inline resume text across ATS layouts.</div>
            </div>
          ` : `
            <div class="column-stack gap-2">
              ${categories.map((cat, cIdx) => `
                <div class="p-2 border rounded bg-surface column-stack gap-2">
                  <div class="flex-row justify-between align-center">
                    <input type="text" class="text-xs font-bold" style="max-width: 180px; padding: 2px 6px;" value="${escapeHtml(cat.name || "")}" placeholder="Category Name" oninput="updateSkillCategoryName(${cIdx}, this.value)">
                    <div class="flex-row align-center gap-1">
                      <button class="icon-btn xs" type="button" onclick="moveSkillCategory(${cIdx}, -1)" ${cIdx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                      <button class="icon-btn xs" type="button" onclick="moveSkillCategory(${cIdx}, 1)" ${cIdx === categories.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                      <button class="icon-btn xs text-danger" type="button" onclick="removeSkillCategory(${cIdx})" title="Remove Category"><i data-lucide="trash-2"></i></button>
                    </div>
                  </div>
                  <input type="text" class="text-xs" value="${escapeHtml((cat.skills || []).join(', '))}" placeholder="Skills for this category (e.g. Excel, PowerBI, SQL)" oninput="updateSkillCategorySkills(${cIdx}, this.value)">
                </div>
              `).join("")}
              <button class="secondary-btn xs align-self-start" type="button" onclick="addSkillCategory()"><i data-lucide="plus"></i><span>Add Skill Category</span></button>
            </div>
          `}
        </div>
      `;
    } else if (secKey === "experiences") {
      icon = "briefcase";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('experiences')"><i data-lucide="plus"></i><span>Add Role</span></button>`;
      const exps = resumeBuilderState.experiences || [];
      bodyHtml = exps.length === 0
        ? '<p class="text-xs text-muted m-0">No experience entries yet. Click "+ Add Role" to add work history.</p>'
        : `<div class="column-stack gap-3">${exps.map((e, idx) => `
            <div class="builder-entry-card ${e.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Role #${idx + 1}</strong>
                  ${e.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('experiences', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('experiences', ${idx}, 1)" ${idx === exps.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('experiences', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!e.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('experiences', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('experiences', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label>Job Title / Role
                  <input type="text" value="${escapeHtml(e.title || "")}" oninput="updateBuilderItemField('experiences', ${idx}, 'title', this.value)">
                </label>
                <label>Company / Organization
                  <input type="text" value="${escapeHtml(e.company || "")}" oninput="updateBuilderItemField('experiences', ${idx}, 'company', this.value)">
                </label>
                <label>Location
                  <input type="text" value="${escapeHtml(e.location || "")}" placeholder="e.g. Remote, City" oninput="updateBuilderItemField('experiences', ${idx}, 'location', this.value)">
                </label>
                <label>Start Date
                  <input type="text" value="${escapeHtml(e.start_date || "")}" placeholder="e.g. May 2023 or 2023" oninput="updateBuilderItemField('experiences', ${idx}, 'start_date', this.value)">
                </label>
                <label>End Date
                  <input type="text" value="${escapeHtml(e.end_date || "")}" placeholder="e.g. Present or 2025" oninput="updateBuilderItemField('experiences', ${idx}, 'end_date', this.value)">
                </label>
                <label class="flex-row align-center gap-2 mt-2">
                  <input type="checkbox" ${e.is_current ? "checked" : ""} onchange="updateBuilderItemField('experiences', ${idx}, 'is_current', this.checked)">
                  <span class="text-xs">I currently work here</span>
                </label>
              </div>
              <div class="mt-2">
                <div class="text-xs text-muted mb-1">Responsibilities & Achievements (Rich Text Bullet Points):</div>
                <div class="rich-text-wrapper">
                  ${renderRichToolbar(`exp-bullets-${idx}`)}
                  <div class="rich-text-content" id="exp-bullets-${idx}" contenteditable="true"
                       data-placeholder="Describe achievements, quantifiable results, or responsibilities..."
                       oninput="updateBuilderItemBullets('experiences', ${idx}, this.innerHTML)">${(e.bullets || []).map(b => `<div>${sanitizeHtmlForPreview(b)}</div>`).join("")}</div>
                </div>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "projects") {
      icon = "folder-git-2";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('projects')"><i data-lucide="plus"></i><span>Add Project</span></button>`;
      const projs = resumeBuilderState.projects || [];
      bodyHtml = projs.length === 0
        ? '<p class="text-xs text-muted m-0">No projects added yet. Click "+ Add Project" to showcase key work.</p>'
        : `<div class="column-stack gap-3">${projs.map((p, idx) => `
            <div class="builder-entry-card ${p.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Project #${idx + 1}</strong>
                  ${p.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('projects', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('projects', ${idx}, 1)" ${idx === projs.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('projects', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!p.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('projects', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('projects', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label>Project Title
                  <input type="text" value="${escapeHtml(p.title || "")}" oninput="updateBuilderItemField('projects', ${idx}, 'title', this.value)">
                </label>
                <label>Skills / Tools / Technologies
                  <input type="text" value="${escapeHtml(p.technologies || "")}" placeholder="e.g. Python, SQL or Financial Modeling" oninput="updateBuilderItemField('projects', ${idx}, 'technologies', this.value)">
                </label>
                <label class="span-2">Project URL / Link
                  <input type="text" value="${escapeHtml(p.url || "")}" placeholder="https://..." oninput="updateBuilderItemField('projects', ${idx}, 'url', this.value)">
                </label>
                <label>Start Date
                  <input type="text" value="${escapeHtml(p.start_date || "")}" placeholder="e.g. 2024" oninput="updateBuilderItemField('projects', ${idx}, 'start_date', this.value)">
                </label>
                <label>End Date
                  <input type="text" value="${escapeHtml(p.end_date || "")}" placeholder="e.g. Present" oninput="updateBuilderItemField('projects', ${idx}, 'end_date', this.value)">
                </label>
              </div>
              <label class="text-xs text-muted mt-2 block">Short Summary:
                <input type="text" value="${escapeHtml(p.description || "")}" oninput="updateBuilderItemField('projects', ${idx}, 'description', this.value)">
              </label>
              <div class="mt-2">
                <div class="text-xs text-muted mb-1">Key Outcomes & Bullets:</div>
                <div class="rich-text-wrapper">
                  ${renderRichToolbar(`proj-bullets-${idx}`)}
                  <div class="rich-text-content" id="proj-bullets-${idx}" contenteditable="true"
                       data-placeholder="Measurable results, accomplishments, or scope..."
                       oninput="updateBuilderItemBullets('projects', ${idx}, this.innerHTML)">${(p.bullets || []).map(b => `<div>${sanitizeHtmlForPreview(b)}</div>`).join("")}</div>
                </div>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "education") {
      icon = "graduation-cap";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('education')"><i data-lucide="plus"></i><span>Add Education</span></button>`;
      const edus = resumeBuilderState.education || [];
      bodyHtml = edus.length === 0
        ? '<p class="text-xs text-muted m-0">No education records added yet. Click "+ Add Education" to add degree.</p>'
        : `<div class="column-stack gap-3">${edus.map((ed, idx) => `
            <div class="builder-entry-card ${ed.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Education #${idx + 1}</strong>
                  ${ed.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('education', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('education', ${idx}, 1)" ${idx === edus.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('education', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!ed.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('education', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('education', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label class="span-2">Institution / University
                  <input type="text" value="${escapeHtml(ed.institution || "")}" oninput="updateBuilderItemField('education', ${idx}, 'institution', this.value)">
                </label>
                <label>Degree
                  <input type="text" value="${escapeHtml(ed.degree || "")}" placeholder="e.g. B.S., B.A., M.B.A., or High School" oninput="updateBuilderItemField('education', ${idx}, 'degree', this.value)">
                </label>
                <label>Field of Study
                  <input type="text" value="${escapeHtml(ed.field_of_study || "")}" placeholder="e.g. Business Administration, Nursing, CS" oninput="updateBuilderItemField('education', ${idx}, 'field_of_study', this.value)">
                </label>
                <label>Start Date / Year
                  <input type="text" value="${escapeHtml(ed.start_date || "")}" placeholder="e.g. 2020" oninput="updateBuilderItemField('education', ${idx}, 'start_date', this.value)">
                </label>
                <label>Graduation Year
                  <input type="text" value="${escapeHtml(ed.end_date || "")}" placeholder="e.g. 2024" oninput="updateBuilderItemField('education', ${idx}, 'end_date', this.value)">
                </label>
                <label class="span-2">Location / Honors / GPA (Optional)
                  <input type="text" value="${escapeHtml(ed.grade || "")}" placeholder="e.g. Magna Cum Laude, GPA 3.8/4.0" oninput="updateBuilderItemField('education', ${idx}, 'grade', this.value)">
                </label>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "certifications") {
      icon = "check-circle-2";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('certifications')"><i data-lucide="plus"></i><span>Add Cert</span></button>`;
      const certs = resumeBuilderState.certifications || [];
      bodyHtml = certs.length === 0
        ? '<p class="text-xs text-muted m-0">No certifications added yet.</p>'
        : `<div class="column-stack gap-3">${certs.map((c, idx) => `
            <div class="builder-entry-card ${c.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Cert #${idx + 1}</strong>
                  ${c.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('certifications', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('certifications', ${idx}, 1)" ${idx === certs.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('certifications', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!c.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('certifications', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('certifications', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label>Certificate / License Name
                  <input type="text" value="${escapeHtml(c.name || "")}" oninput="updateBuilderItemField('certifications', ${idx}, 'name', this.value)">
                </label>
                <label>Issuing Organization
                  <input type="text" value="${escapeHtml(c.issuer || "")}" placeholder="e.g. PMI, State Board, AWS" oninput="updateBuilderItemField('certifications', ${idx}, 'issuer', this.value)">
                </label>
                <label class="span-2">Issue Date / Year
                  <input type="text" value="${escapeHtml(c.date || "")}" placeholder="e.g. 2024" oninput="updateBuilderItemField('certifications', ${idx}, 'date', this.value)">
                </label>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "achievements") {
      icon = "trophy";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('achievements')"><i data-lucide="plus"></i><span>Add Achievement</span></button>`;
      const achs = resumeBuilderState.achievements || [];
      bodyHtml = achs.length === 0
        ? '<p class="text-xs text-muted m-0">No achievements added yet.</p>'
        : `<div class="column-stack gap-2">${achs.map((a, idx) => {
            const val = typeof a === "string" ? a : (a.text || "");
            const isHid = typeof a === "object" ? !!a.is_hidden : false;
            return `
              <div class="flex-row align-center gap-2 ${isHid ? "opacity-50" : ""}">
                <input type="text" value="${escapeHtml(val)}" placeholder="e.g. Exceeded annual sales quota by 135% in FY2024" oninput="updateBuilderAchievement(${idx}, this.value)" style="flex: 1;">
                <label class="text-xs flex-row align-center gap-1" style="cursor: pointer;">
                  <input type="checkbox" ${!isHid ? "checked" : ""} onchange="toggleBuilderEntryVisibility('achievements', ${idx}, !this.checked)">
                  <span>Visible</span>
                </label>
                <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('achievements', ${idx})"><i data-lucide="trash-2"></i></button>
              </div>
            `;
          }).join("")}</div>`;
    } else if (secKey === "awards") {
      icon = "award";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('awards')"><i data-lucide="plus"></i><span>Add Award</span></button>`;
      const awds = resumeBuilderState.awards || [];
      bodyHtml = awds.length === 0
        ? '<p class="text-xs text-muted m-0">No awards added yet.</p>'
        : `<div class="column-stack gap-2">${awds.map((a, idx) => {
            const val = typeof a === "string" ? a : (a.text || "");
            const isHid = typeof a === "object" ? !!a.is_hidden : false;
            return `
              <div class="flex-row align-center gap-2 ${isHid ? "opacity-50" : ""}">
                <input type="text" value="${escapeHtml(val)}" placeholder="e.g. Employee of the Year 2023" oninput="updateBuilderAward(${idx}, this.value)" style="flex: 1;">
                <label class="text-xs flex-row align-center gap-1" style="cursor: pointer;">
                  <input type="checkbox" ${!isHid ? "checked" : ""} onchange="toggleBuilderEntryVisibility('awards', ${idx}, !this.checked)">
                  <span>Visible</span>
                </label>
                <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('awards', ${idx})"><i data-lucide="trash-2"></i></button>
              </div>
            `;
          }).join("")}</div>`;
    } else if (secKey === "languages") {
      icon = "languages";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('languages')"><i data-lucide="plus"></i><span>Add Language</span></button>`;
      const langs = resumeBuilderState.languages || [];
      bodyHtml = langs.length === 0
        ? '<p class="text-xs text-muted m-0">No languages added yet.</p>'
        : `<div class="column-stack gap-2">${langs.map((l, idx) => `
            <div class="flex-row align-center gap-2 ${l.is_hidden ? "opacity-50" : ""}">
              <input type="text" value="${escapeHtml(l.language || "")}" placeholder="Language (e.g. Spanish)" oninput="updateBuilderItemField('languages', ${idx}, 'language', this.value)" style="flex: 1;">
              <input type="text" value="${escapeHtml(l.proficiency || "")}" placeholder="e.g. Fluent, Native, Professional" oninput="updateBuilderItemField('languages', ${idx}, 'proficiency', this.value)" style="width: 160px;">
              <label class="text-xs flex-row align-center gap-1" style="cursor: pointer;">
                <input type="checkbox" ${!l.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('languages', ${idx}, !this.checked)">
                <span>Visible</span>
              </label>
              <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('languages', ${idx})"><i data-lucide="trash-2"></i></button>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "volunteer") {
      icon = "heart";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('volunteer')"><i data-lucide="plus"></i><span>Add Entry</span></button>`;
      const vols = resumeBuilderState.volunteer || [];
      bodyHtml = vols.length === 0
        ? '<p class="text-xs text-muted m-0">No volunteer experience added yet.</p>'
        : `<div class="column-stack gap-3">${vols.map((v, idx) => `
            <div class="builder-entry-card ${v.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Volunteer Entry #${idx + 1}</strong>
                  ${v.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('volunteer', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('volunteer', ${idx}, 1)" ${idx === vols.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('volunteer', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!v.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('volunteer', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('volunteer', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label>Role / Title
                  <input type="text" value="${escapeHtml(v.role || "")}" oninput="updateBuilderItemField('volunteer', ${idx}, 'role', this.value)">
                </label>
                <label>Organization
                  <input type="text" value="${escapeHtml(v.organization || "")}" oninput="updateBuilderItemField('volunteer', ${idx}, 'organization', this.value)">
                </label>
                <label>Location
                  <input type="text" value="${escapeHtml(v.location || "")}" placeholder="e.g. City" oninput="updateBuilderItemField('volunteer', ${idx}, 'location', this.value)">
                </label>
                <label>Start Date
                  <input type="text" value="${escapeHtml(v.start_date || "")}" placeholder="e.g. 2022" oninput="updateBuilderItemField('volunteer', ${idx}, 'start_date', this.value)">
                </label>
                <label>End Date
                  <input type="text" value="${escapeHtml(v.end_date || "")}" placeholder="e.g. Present" oninput="updateBuilderItemField('volunteer', ${idx}, 'end_date', this.value)">
                </label>
                <label class="flex-row align-center gap-2 mt-2">
                  <input type="checkbox" ${v.is_current ? "checked" : ""} onchange="updateBuilderItemField('volunteer', ${idx}, 'is_current', this.checked)">
                  <span class="text-xs">Current involvement</span>
                </label>
              </div>
              <div class="mt-2">
                <div class="text-xs text-muted mb-1">Description & Bullet Points:</div>
                <div class="rich-text-wrapper">
                  ${renderRichToolbar(`vol-bullets-${idx}`)}
                  <div class="rich-text-content" id="vol-bullets-${idx}" contenteditable="true"
                       data-placeholder="Impact, responsibilities, or activities..."
                       oninput="updateBuilderItemBullets('volunteer', ${idx}, this.innerHTML)">${(v.bullets || []).map(b => `<div>${sanitizeHtmlForPreview(b)}</div>`).join("")}</div>
                </div>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "leadership") {
      icon = "users";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('leadership')"><i data-lucide="plus"></i><span>Add Activity</span></button>`;
      const leads = resumeBuilderState.leadership || [];
      bodyHtml = leads.length === 0
        ? '<p class="text-xs text-muted m-0">No leadership activities added yet.</p>'
        : `<div class="column-stack gap-3">${leads.map((l, idx) => `
            <div class="builder-entry-card ${l.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Leadership #${idx + 1}</strong>
                  ${l.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('leadership', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('leadership', ${idx}, 1)" ${idx === leads.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('leadership', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!l.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('leadership', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('leadership', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label>Role / Position
                  <input type="text" value="${escapeHtml(l.role || "")}" oninput="updateBuilderItemField('leadership', ${idx}, 'role', this.value)">
                </label>
                <label>Organization / Committee
                  <input type="text" value="${escapeHtml(l.organization || "")}" oninput="updateBuilderItemField('leadership', ${idx}, 'organization', this.value)">
                </label>
                <label>Location
                  <input type="text" value="${escapeHtml(l.location || "")}" placeholder="e.g. City" oninput="updateBuilderItemField('leadership', ${idx}, 'location', this.value)">
                </label>
                <label>Date / Term
                  <input type="text" value="${escapeHtml(l.start_date || "")}" placeholder="e.g. 2023 - 2024" oninput="updateBuilderItemField('leadership', ${idx}, 'start_date', this.value)">
                </label>
              </div>
              <div class="mt-2">
                <div class="text-xs text-muted mb-1">Impact & Details:</div>
                <div class="rich-text-wrapper">
                  ${renderRichToolbar(`lead-bullets-${idx}`)}
                  <div class="rich-text-content" id="lead-bullets-${idx}" contenteditable="true"
                       data-placeholder="Achievements, initiatives led, or responsibilities..."
                       oninput="updateBuilderItemBullets('leadership', ${idx}, this.innerHTML)">${(l.bullets || []).map(b => `<div>${sanitizeHtmlForPreview(b)}</div>`).join("")}</div>
                </div>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "publications") {
      icon = "book-open";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('publications')"><i data-lucide="plus"></i><span>Add Publication</span></button>`;
      const pubs = resumeBuilderState.publications || [];
      bodyHtml = pubs.length === 0
        ? '<p class="text-xs text-muted m-0">No publications added yet.</p>'
        : `<div class="column-stack gap-3">${pubs.map((pb, idx) => `
            <div class="builder-entry-card ${pb.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Publication #${idx + 1}</strong>
                  ${pb.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('publications', ${idx}, -1)" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('publications', ${idx}, 1)" ${idx === pubs.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('publications', ${idx})" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!pb.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('publications', ${idx}, !this.checked)">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('publications', ${idx})" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label class="span-2">Publication / Paper Title
                  <input type="text" value="${escapeHtml(pb.title || "")}" oninput="updateBuilderItemField('publications', ${idx}, 'title', this.value)">
                </label>
                <label>Publisher / Journal / Conference
                  <input type="text" value="${escapeHtml(pb.publisher || "")}" oninput="updateBuilderItemField('publications', ${idx}, 'publisher', this.value)">
                </label>
                <label>Publication Date / Year
                  <input type="text" value="${escapeHtml(pb.date || "")}" placeholder="e.g. 2024" oninput="updateBuilderItemField('publications', ${idx}, 'date', this.value)">
                </label>
                <label class="span-2">DOI / URL Link
                  <input type="text" value="${escapeHtml(pb.url || "")}" placeholder="https://..." oninput="updateBuilderItemField('publications', ${idx}, 'url', this.value)">
                </label>
              </div>
            </div>
          `).join("")}</div>`;
    } else if (secKey === "courses") {
      icon = "bookmark";
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('courses')"><i data-lucide="plus"></i><span>Add Course</span></button>`;
      const crss = resumeBuilderState.courses || [];
      bodyHtml = crss.length === 0
        ? '<p class="text-xs text-muted m-0">No courses added yet.</p>'
        : `<div class="column-stack gap-2">${crss.map((cs, idx) => `
            <div class="flex-row align-center gap-2 ${cs.is_hidden ? "opacity-50" : ""}">
              <input type="text" value="${escapeHtml(cs.name || "")}" placeholder="Course Name (e.g. Advanced Corporate Finance)" oninput="updateBuilderItemField('courses', ${idx}, 'name', this.value)" style="flex: 1;">
              <input type="text" value="${escapeHtml(cs.institution || "")}" placeholder="Institution / Provider" oninput="updateBuilderItemField('courses', ${idx}, 'institution', this.value)" style="width: 160px;">
              <label class="text-xs flex-row align-center gap-1" style="cursor: pointer;">
                <input type="checkbox" ${!cs.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('courses', ${idx}, !this.checked)">
                <span>Visible</span>
              </label>
              <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('courses', ${idx})"><i data-lucide="trash-2"></i></button>
            </div>
          `).join("")}</div>`;
    } else if (secKey.startsWith("custom_")) {
      icon = "sparkles";
      const csObj = (resumeBuilderState.customSections || []).find(c => c.id === secKey) || { id: secKey, title: secTitle, items: [] };
      addBtnHtml = `<button class="secondary-btn xs" type="button" onclick="addBuilderEntry('custom', '${secKey}')"><i data-lucide="plus"></i><span>Add Entry</span></button>`;
      const items = csObj.items || [];
      bodyHtml = items.length === 0
        ? '<p class="text-xs text-muted m-0">No entries in this custom section yet. Click "+ Add Entry" to add content.</p>'
        : `<div class="column-stack gap-3">${items.map((it, idx) => `
            <div class="builder-entry-card ${it.is_hidden ? "is-hidden-entry" : ""}">
              <div class="builder-entry-toolbar">
                <div class="flex-row align-center gap-1">
                  <strong class="text-xs">Entry #${idx + 1}</strong>
                  ${it.is_hidden ? '<span class="builder-badge-hidden">Hidden from resume</span>' : ''}
                </div>
                <div class="builder-entry-actions">
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('custom', ${idx}, -1, '${secKey}')" ${idx === 0 ? "disabled" : ""} title="Move Up"><i data-lucide="arrow-up"></i></button>
                  <button class="icon-btn xs" type="button" onclick="moveBuilderEntry('custom', ${idx}, 1, '${secKey}')" ${idx === items.length - 1 ? "disabled" : ""} title="Move Down"><i data-lucide="arrow-down"></i></button>
                  <button class="icon-btn xs" type="button" onclick="duplicateBuilderEntry('custom', ${idx}, '${secKey}')" title="Duplicate"><i data-lucide="copy"></i></button>
                  <label class="flex-row align-center gap-1 text-xs" style="margin: 0 4px; cursor: pointer;">
                    <input type="checkbox" ${!it.is_hidden ? "checked" : ""} onchange="toggleBuilderEntryVisibility('custom', ${idx}, !this.checked, '${secKey}')">
                    <span>Visible</span>
                  </label>
                  <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderItem('custom', ${idx}, '${secKey}')" title="Delete"><i data-lucide="trash-2"></i></button>
                </div>
              </div>
              <div class="form-grid">
                <label class="span-2">Title / Name
                  <input type="text" value="${escapeHtml(it.title || "")}" oninput="updateBuilderItemField('custom', ${idx}, 'title', this.value, '${secKey}')">
                </label>
                <label>Subtitle / Organization / Scope
                  <input type="text" value="${escapeHtml(it.subtitle || "")}" oninput="updateBuilderItemField('custom', ${idx}, 'subtitle', this.value, '${secKey}')">
                </label>
                <label>Date / Year
                  <input type="text" value="${escapeHtml(it.date || "")}" placeholder="e.g. 2024" oninput="updateBuilderItemField('custom', ${idx}, 'date', this.value, '${secKey}')">
                </label>
              </div>
              <div class="mt-2">
                <div class="text-xs text-muted mb-1">Details & Bullet Points:</div>
                <div class="rich-text-wrapper">
                  ${renderRichToolbar(`custom-bullets-${secKey}-${idx}`)}
                  <div class="rich-text-content" id="custom-bullets-${secKey}-${idx}" contenteditable="true"
                       data-placeholder="Description or bullet points..."
                       oninput="updateBuilderItemBullets('custom', ${idx}, this.innerHTML, '${secKey}')">${(it.bullets || []).map(b => `<div>${sanitizeHtmlForPreview(b)}</div>`).join("")}</div>
                </div>
              </div>
            </div>
          `).join("")}</div>`;
    }

    return `
      <div class="panel" id="secEditor-${secKey}">
        <div class="panel-head flex-row justify-between align-center">
          <div class="flex-row align-center gap-2">
            <i data-lucide="${icon}"></i>
            <input type="text" class="sec-title-input" value="${escapeHtml(secTitle)}"
                   onchange="updateBuilderSectionTitle('${secKey}', this.value)"
                   placeholder="Section Title" title="Click to rename section">
          </div>
          <div class="sec-header-actions">
            <button class="icon-btn xs" type="button" onclick="moveBuilderSection('${secKey}', -1)" ${isFirst ? "disabled" : ""} title="Move section up">
              <i data-lucide="arrow-up"></i>
            </button>
            <button class="icon-btn xs" type="button" onclick="moveBuilderSection('${secKey}', 1)" ${isLast ? "disabled" : ""} title="Move section down">
              <i data-lucide="arrow-down"></i>
            </button>
            ${addBtnHtml}
            <button class="icon-btn xs text-danger" type="button" onclick="removeBuilderSection('${secKey}')" title="Remove section from resume">
              <i data-lucide="trash-2"></i>
            </button>
            <button class="icon-btn xs" type="button" onclick="this.closest('.panel').querySelector('.panel-body').classList.toggle('hidden')" title="Toggle section">
              <i data-lucide="chevron-down"></i>
            </button>
          </div>
        </div>
        <div class="panel-body">
          ${bodyHtml}
        </div>
      </div>
    `;
  }).join("");

  drawIcons();
}

function renderResumePreviewCanvas() {
  const canvas = $("#builderPreviewCanvas");
  if (!canvas) return;

  const sheet = $("#builderLivePreviewSheet");
  if (sheet) {
    sheet.className = `resume-preview-sheet tpl-${resumeBuilderState.template || "classic_ats"}`;
  }

  applyCustomizerStylesToCanvas();

  const h = resumeBuilderState.header || {};
  const nameEl = $("#prevCanvasName");
  if (nameEl) nameEl.textContent = h.full_name || "Candidate Name";

  const headEl = $("#prevCanvasHeadline");
  if (headEl) headEl.textContent = h.headline || "";

  const contactEl = $("#prevCanvasContact");
  if (contactEl) {
    contactEl.innerHTML = "";
    const parts = [];

    if (h.location) parts.push({ text: h.location });
    if (h.phone) parts.push({ text: h.phone, href: `tel:${h.phone}` });
    if (h.email) parts.push({ text: h.email, href: `mailto:${h.email}` });

    if (h.linkedin) {
      const clean = h.linkedin.replace(/^https?:\/\/(www\.)?/, "");
      parts.push({ text: clean, href: h.linkedin.startsWith("http") ? h.linkedin : `https://${h.linkedin}` });
    }
    if (h.github) {
      const clean = h.github.replace(/^https?:\/\/(www\.)?/, "");
      parts.push({ text: clean, href: h.github.startsWith("http") ? h.github : `https://${h.github}` });
    }
    if (h.website) {
      const clean = h.website.replace(/^https?:\/\/(www\.)?/, "");
      parts.push({ text: clean, href: h.website.startsWith("http") ? h.website : `https://${h.website}` });
    }

    parts.forEach((p, idx) => {
      if (idx > 0) {
        const sep = document.createElement("span");
        sep.className = "prev-contact-sep";
        sep.textContent = "|";
        contactEl.appendChild(sep);
      }
      if (p.href) {
        const a = document.createElement("a");
        a.href = p.href;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = p.text;
        contactEl.appendChild(a);
      } else {
        const span = document.createElement("span");
        span.textContent = p.text;
        contactEl.appendChild(span);
      }
    });
  }

  const container = $("#prevSectionsContainer");
  if (!container) return;
  container.innerHTML = "";

  const sectionOrder = resumeBuilderState.sectionOrder || ["summary", "skills", "experiences", "projects", "education", "certifications", "achievements", "languages"];
  const titles = resumeBuilderState.sectionTitles || {};
  const fmt = resumeBuilderState.dateFormat || "MMM YYYY";

  sectionOrder.forEach(secKey => {
    const secTitle = titles[secKey] || DEFAULT_SECTION_TITLES[secKey] || "Section";

    if (secKey === "summary") {
      const sum = (resumeBuilderState.summary || "").trim();
      const textClean = sum.replace(/<[^>]+>/g, "").trim();
      if (textClean) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="resume-summary-text text-xs" style="line-height: var(--resume-line-height); margin: 0; color: #374151;">${sanitizeHtmlForPreview(sum)}</div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "skills") {
      const isGrouped = resumeBuilderState.skillsLayout === "grouped";
      const categories = (resumeBuilderState.skillCategories || []).filter(c => c && c.name && c.skills && c.skills.length > 0);
      const skills = (resumeBuilderState.skills || []).filter(s => s && s.trim());

      if (isGrouped && categories.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-skills-container prev-skills-grouped column-stack gap-1">
            ${categories.map(c => `
              <div class="prev-skills-text text-xs" style="line-height: var(--resume-line-height); margin: 0; color: #374151;">
                <strong>${escapeHtml(c.name)}:</strong> ${escapeHtml(c.skills.join(", "))}
              </div>
            `).join("")}
          </div>
        `;
        container.appendChild(sec);
      } else if (skills.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-skills-container">
            <p class="prev-skills-text text-xs" style="line-height: var(--resume-line-height); margin: 0; color: #374151;">
              ${skills.map(s => escapeHtml(s)).join(", ")}
            </p>
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "experiences") {
      const exps = (resumeBuilderState.experiences || []).filter(e => !e.is_hidden && (e.company || e.title));
      if (exps.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${exps.map(e => {
              const dateStr = formatClientDateRange(e.start_date, e.end_date, e.is_current, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(e.title || "Role")}</strong>${e.company ? ` — ${escapeHtml(e.company)}` : ""}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${e.location ? `<div class="prev-item-sub">${escapeHtml(e.location)}</div>` : ""}
                  ${(e.bullets || []).filter(b => b && b.trim()).length > 0 ? `
                    <ul class="prev-item-bullets">
                      ${e.bullets.filter(b => b && b.trim()).map(b => `<li>${sanitizeHtmlForPreview(b)}</li>`).join("")}
                    </ul>
                  ` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "projects") {
      const projs = (resumeBuilderState.projects || []).filter(p => !p.is_hidden && p.title);
      if (projs.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${projs.map(p => {
              const dateStr = formatClientDateRange(p.start_date, p.end_date, false, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(p.title)}</strong>${p.technologies ? ` <span class="text-muted" style="font-weight: 400; font-size: 0.9em;">| ${escapeHtml(p.technologies)}</span>` : ""}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${p.description ? `<p class="text-xs" style="margin: 2px 0; color: #374151;">${sanitizeHtmlForPreview(p.description)}</p>` : ""}
                  ${(p.bullets || []).filter(b => b && b.trim()).length > 0 ? `
                    <ul class="prev-item-bullets">
                      ${p.bullets.filter(b => b && b.trim()).map(b => `<li>${sanitizeHtmlForPreview(b)}</li>`).join("")}
                    </ul>
                  ` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "education") {
      const edus = (resumeBuilderState.education || []).filter(ed => !ed.is_hidden && (ed.institution || ed.degree));
      if (edus.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${edus.map(ed => {
              const dateStr = formatClientDateRange(ed.start_date, ed.end_date, false, fmt);
              const deg = ed.degree ? `<strong>${escapeHtml(ed.degree)}</strong>` : "";
              const field = ed.field_of_study ? ` in ${escapeHtml(ed.field_of_study)}` : "";
              const titleStr = deg + field + (ed.institution ? ` — ${escapeHtml(ed.institution)}` : "");
              const meta = [ed.location, ed.grade ? `Honors / GPA: ${ed.grade}` : ""].filter(Boolean).join(" | ");
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col">${titleStr}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${meta ? `<div class="prev-item-sub">${escapeHtml(meta)}</div>` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "certifications") {
      const certs = (resumeBuilderState.certifications || []).filter(c => !c.is_hidden && (c.name && c.name.trim()));
      if (certs.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${certs.map(c => {
              const d = formatDateStrClient(c.date, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(c.name)}</strong>${c.issuer ? ` — ${escapeHtml(c.issuer)}` : ""}</span>
                    ${d ? `<span class="prev-item-date">${escapeHtml(d)}</span>` : ""}
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "achievements") {
      const achs = (resumeBuilderState.achievements || []).filter(a => {
        if (typeof a === "string") return a && a.trim();
        return !a.is_hidden && a.text && a.text.trim();
      });
      if (achs.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <ul class="prev-item-bullets">
            ${achs.map(a => `<li>${sanitizeHtmlForPreview(typeof a === "string" ? a : a.text)}</li>`).join("")}
          </ul>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "awards") {
      const awds = (resumeBuilderState.awards || []).filter(a => {
        if (typeof a === "string") return a && a.trim();
        return !a.is_hidden && a.text && a.text.trim();
      });
      if (awds.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <ul class="prev-item-bullets">
            ${awds.map(a => `<li>${sanitizeHtmlForPreview(typeof a === "string" ? a : a.text)}</li>`).join("")}
          </ul>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "languages") {
      const langs = (resumeBuilderState.languages || []).filter(l => !l.is_hidden && (l.language && l.language.trim()));
      if (langs.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <p class="text-xs" style="color: #374151; margin: 0; line-height: var(--resume-line-height);">
            ${langs.map(l => `<strong>${escapeHtml(l.language)}</strong>${l.proficiency ? ` (${escapeHtml(l.proficiency)})` : ""}`).join(" • ")}
          </p>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "volunteer") {
      const vols = (resumeBuilderState.volunteer || []).filter(v => !v.is_hidden && (v.organization || v.role));
      if (vols.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${vols.map(v => {
              const dateStr = formatClientDateRange(v.start_date, v.end_date, v.is_current, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(v.role || "Volunteer")}</strong>${v.organization ? ` — ${escapeHtml(v.organization)}` : ""}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${v.location ? `<div class="prev-item-sub">${escapeHtml(v.location)}</div>` : ""}
                  ${(v.bullets || []).filter(b => b && b.trim()).length > 0 ? `
                    <ul class="prev-item-bullets">
                      ${v.bullets.filter(b => b && b.trim()).map(b => `<li>${sanitizeHtmlForPreview(b)}</li>`).join("")}
                    </ul>
                  ` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "leadership") {
      const leads = (resumeBuilderState.leadership || []).filter(l => !l.is_hidden && (l.organization || l.role));
      if (leads.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${leads.map(l => {
              const dateStr = formatDateStrClient(l.start_date, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(l.role || "Leader")}</strong>${l.organization ? ` — ${escapeHtml(l.organization)}` : ""}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${(l.bullets || []).filter(b => b && b.trim()).length > 0 ? `
                    <ul class="prev-item-bullets">
                      ${l.bullets.filter(b => b && b.trim()).map(b => `<li>${sanitizeHtmlForPreview(b)}</li>`).join("")}
                    </ul>
                  ` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "publications") {
      const pubs = (resumeBuilderState.publications || []).filter(pb => !pb.is_hidden && pb.title);
      if (pubs.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${pubs.map(pb => {
              const dateStr = formatDateStrClient(pb.date, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(pb.title)}</strong>${pb.publisher ? ` — <em>${escapeHtml(pb.publisher)}</em>` : ""}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${pb.url ? `<div class="prev-item-sub"><a href="${escapeHtml(pb.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(pb.url)}</a></div>` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    } else if (secKey === "courses") {
      const crss = (resumeBuilderState.courses || []).filter(cs => !cs.is_hidden && cs.name);
      if (crss.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <p class="text-xs" style="color: #374151; margin: 0; line-height: var(--resume-line-height);">
            ${crss.map(cs => `${escapeHtml(cs.name)}${cs.institution ? ` (${escapeHtml(cs.institution)})` : ""}`).join(" • ")}
          </p>
        `;
        container.appendChild(sec);
      }
    } else if (secKey.startsWith("custom_")) {
      const csObj = (resumeBuilderState.customSections || []).find(c => c.id === secKey);
      const items = (csObj && csObj.items ? csObj.items : []).filter(it => !it.is_hidden && (it.title || it.description || (it.bullets && it.bullets.length > 0)));
      if (items.length > 0) {
        const sec = document.createElement("div");
        sec.className = "prev-section";
        sec.innerHTML = `
          <h3 class="preview-section-title">${escapeHtml(secTitle)}</h3>
          <div class="prev-items-list">
            ${items.map(it => {
              const dateStr = formatDateStrClient(it.date, fmt);
              return `
                <div class="prev-item-entry">
                  <div class="prev-item-header">
                    <span class="prev-item-title-col"><strong>${escapeHtml(it.title || "")}</strong>${it.subtitle ? ` — ${escapeHtml(it.subtitle)}` : ""}</span>
                    ${dateStr ? `<span class="prev-item-date">${escapeHtml(dateStr)}</span>` : ""}
                  </div>
                  ${(it.bullets || []).filter(b => b && b.trim()).length > 0 ? `
                    <ul class="prev-item-bullets">
                      ${it.bullets.filter(b => b && b.trim()).map(b => `<li>${sanitizeHtmlForPreview(b)}</li>`).join("")}
                    </ul>
                  ` : ""}
                </div>
              `;
            }).join("")}
          </div>
        `;
        container.appendChild(sec);
      }
    }
  });
}

function applyCustomizerStylesToCanvas() {
  const canvas = $("#builderPreviewCanvas");
  if (!canvas) return;

  const font = resumeBuilderState.fontSize || "medium";
  const spacing = resumeBuilderState.spacing || "standard";
  const accent = resumeBuilderState.accentColor || "#1e3a8a";

  const fontSizes = { small: "11.5px", medium: "13px", large: "14.5px" };
  const lineHeights = { compact: "1.25", standard: "1.4", relaxed: "1.55" };
  const spacings = { compact: "8px", standard: "12px", relaxed: "18px" };

  canvas.style.setProperty("--resume-font-size", fontSizes[font] || "13px");
  canvas.style.setProperty("--resume-line-height", lineHeights[spacing] || "1.4");
  canvas.style.setProperty("--resume-spacing", spacings[spacing] || "12px");
  canvas.style.setProperty("--resume-accent", accent);

  const divider = $("#prevCanvasDivider");
  if (divider) divider.style.background = accent;
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
  state.activeJobContext = {
    role: job.title,
    company: job.company,
    companyUrl: "",
    jobUrl: job.job_url || "",
    jobDescription: job.raw_description || "",
    versionId: null,
    jobId: job.id,
    verification: null,
  };
  syncInterviewContextUI();
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
          <button class="secondary-btn xs" type="button" data-prep-app="${app.id}" title="Practice interview for this job"><i data-lucide="messages-square"></i> Interview</button>
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
    card.querySelector(`[data-prep-app="${app.id}"]`)?.addEventListener("click", () => {
      state.activeJobContext = {
        role: app.job_title,
        company: app.company,
        companyUrl: "",
        jobUrl: app.job_url || "",
        jobId: app.job_posting_id || null,
        versionId: app.application_version_id || null,
        verification: null,
      };
      syncInterviewContextUI();
      navigateToTab("interview");
    });
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
  $("#upgradeBtn")?.addEventListener("click", () => navigateToTab("billing"));

  // Currency Selector
  $("#currencySelector")?.addEventListener("change", (e) => {
    state.selectedCurrency = e.target.value;
    updateCurrencyDisplay();
  });

  // ₹1 One-Time Export (Separate from recurring mandate)
  $("#checkoutSingleExportBtn")?.addEventListener("click", handleOneTimeExportPayment);

  // Pro Upgrade buttons
  $("#upgradeProBtn")?.addEventListener("click", () => openRecurringConsentModal("PRO_MONTHLY"));
  $("#upgradeAnnualBtn")?.addEventListener("click", () => openRecurringConsentModal("PRO_ANNUAL"));

  // Recurring Consent Modal interactions
  $("#closeConsentModalBtn")?.addEventListener("click", closeRecurringConsentModal);
  $("#cancelConsentBtn")?.addEventListener("click", closeRecurringConsentModal);
  $("#consentAcknowledgeCheck")?.addEventListener("change", (e) => {
    const confirmBtn = $("#confirmConsentBtn");
    if (confirmBtn) confirmBtn.disabled = !e.target.checked;
  });
  $("#confirmConsentBtn")?.addEventListener("click", () => {
    const planKey = state.pendingPlanKey;
    closeRecurringConsentModal();
    if (planKey) handleUpgrade(planKey);
  });

  // Manage Subscription: UPI AutoPay Modal
  $("#manageAutoPayBtn")?.addEventListener("click", openUpiAutoPayModal);
  $("#closeUpiModalBtn")?.addEventListener("click", closeUpiAutoPayModal);
  $("#closeUpiModalFooterBtn")?.addEventListener("click", closeUpiAutoPayModal);

  // Manage Subscription: Card Renewal Cancellation
  $("#cancelCardRenewalBtn")?.addEventListener("click", handleCancelCardRenewal);

  // Payment Failure: Retry Payment
  $("#retryPaymentBtn")?.addEventListener("click", handleRetryPayment);

  // Payment History Refresh
  $("#refreshPaymentHistoryBtn")?.addEventListener("click", loadPaymentHistory);
}

async function loadPricingData() {
  try {
    const data = await API.request("/payments/pricing");
    state.pricingData = data;
    updateCurrencyDisplay();
  } catch (_) {}
}

function updateCurrencyDisplay() {
  const curr = state.selectedCurrency || "INR";
  const p = state.pricingData?.currencies?.[curr] || { symbol: "₹", single: 1, pro_monthly: 49, pro_annual: 399, pack_10: 29, pack_20: 49, pack_50: 99 };

  if ($("#priceSingleExport")) $("#priceSingleExport").innerHTML = `${p.symbol}${p.single}`;
  $$(".single-price-inline").forEach((el) => { el.textContent = `${p.symbol}${p.single}`; });
  if ($("#priceProMonthly")) $("#priceProMonthly").innerHTML = `${p.symbol}${p.pro_monthly} <span>/ month</span>`;
  if ($("#priceProAnnual")) $("#priceProAnnual").innerHTML = `${p.symbol}${p.pro_annual} <span>/ year</span>`;
  if ($("#pricePack10")) $("#pricePack10").textContent = `${p.symbol}${p.pack_10}`;
  if ($("#pricePack20")) $("#pricePack20").textContent = `${p.symbol}${p.pack_20}`;
  if ($("#pricePack50")) $("#pricePack50").textContent = `${p.symbol}${p.pack_50}`;
}

async function openRecurringConsentModal(planKey) {
  state.pendingPlanKey = planKey;
  const curr = state.selectedCurrency || "INR";
  try {
    const info = await API.request(`/payments/consent-info?plan=${planKey}&currency=${curr}`);
    if ($("#consentPlanName")) $("#consentPlanName").textContent = info.display_name;
    if ($("#consentAmount")) $("#consentAmount").textContent = `${info.currency_symbol}${info.amount} / ${info.frequency || "period"}`;
    if ($("#consentFrequency")) $("#consentFrequency").textContent = capitalize(info.billing_frequency || info.frequency);
    if ($("#consentRenewalDate")) $("#consentRenewalDate").textContent = `${info.next_renewal_days} days from today`;
    if ($("#consentAuthAmount")) $("#consentAuthAmount").textContent = `${info.currency_symbol}1 (recurring mandate setup)`;
    if ($("#consentNoticeText")) $("#consentNoticeText").textContent = info.regulatory_note || info.mandate_notice;
  } catch (_) {
    if ($("#consentPlanName")) $("#consentPlanName").textContent = planKey === "PRO_ANNUAL" ? "Annual Power Plan" : "Pro Monthly Plan";
    if ($("#consentAmount")) $("#consentAmount").textContent = planKey === "PRO_ANNUAL" ? "₹399 / year" : "₹49 / month";
    if ($("#consentFrequency")) $("#consentFrequency").textContent = planKey === "PRO_ANNUAL" ? "Annual" : "Monthly";
    if ($("#consentRenewalDate")) $("#consentRenewalDate").textContent = planKey === "PRO_ANNUAL" ? "365 days from today" : "30 days from today";
    if ($("#consentAuthAmount")) $("#consentAuthAmount").textContent = "₹1 (recurring mandate setup)";
    if ($("#consentNoticeText")) $("#consentNoticeText").textContent = "₹1 authorisation is for setting up recurring payment authorization. It is not a one-time resume export. You can manage or cancel renewals at any time from your subscription dashboard.";
  }

  if ($("#consentAcknowledgeCheck")) $("#consentAcknowledgeCheck").checked = false;
  if ($("#confirmConsentBtn")) $("#confirmConsentBtn").disabled = true;
  const modal = $("#recurringConsentModal");
  if (modal) modal.classList.remove("hidden");
  drawIcons();
}

function closeRecurringConsentModal() {
  const modal = $("#recurringConsentModal");
  if (modal) modal.classList.add("hidden");
  state.pendingPlanKey = null;
}

function openUpiAutoPayModal() {
  const modal = $("#upiAutoPayModal");
  if (modal) modal.classList.remove("hidden");
  drawIcons();
}

function closeUpiAutoPayModal() {
  const modal = $("#upiAutoPayModal");
  if (modal) modal.classList.add("hidden");
}

// ₹1 Standalone One-Time Export (Non-recurring, No mandate)
async function handleOneTimeExportPayment() {
  const btn = $("#checkoutSingleExportBtn");
  const origHtml = btn ? btn.innerHTML : `<span>Purchase 1 Export (₹1)</span>`;
  setButtonLoading(btn, true, "Processing order...");
  try {
    const order = await API.request("/payments/create-order", {
      method: "POST",
      body: { plan: "SINGLE_EXPORT", currency: state.selectedCurrency || "INR" },
    });

    if (order.is_test || order.provider === "mock" || order.payment_mode === "test") {
      const verifyRes = await API.request("/payments/verify", {
        method: "POST",
        body: {
          order_id: order.order_id,
          payment_id: `pay_order_${order.order_id}`,
          plan: "SINGLE_EXPORT",
        },
      });
      toast(verifyRes.message || "1 resume export credit added to your account.", "success");
      await loadBillingSummary();
      await loadPaymentHistory();
      renderDashboard();
      return;
    }

    if (!window.Razorpay) {
      return toast("Payment gateway is initializing. Please try again.", "error");
    }
    const rzp = new window.Razorpay({
      key: order.razorpay_key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.order_id,
      name: "SmartResume.ai",
      description: "One-Time Resume Export (Non-recurring)",
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
    if (btn) {
      btn.innerHTML = origHtml;
      btn.disabled = false;
    }
  }
}

async function handleUpgrade(planKey) {
  try {
    const order = await API.request("/payments/create-order", {
      method: "POST",
      body: { plan: planKey, currency: state.selectedCurrency || "INR" },
    });

    if (order.provider === "mock" || order.is_test) {
      state.user = await API.request("/users/profile");
      renderUserBar();
      toast("Plan upgraded successfully!");
      await loadBillingSummary();
      await loadPaymentHistory();
      renderDashboard();
      return;
    }

    if (!window.Razorpay) {
      return toast("Payment gateway is initializing. Please try again.", "error");
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
  const sub = data.subscription || {};
  const q = data.quotas || {};
  const fits = q.fit_analyses || { used: 0, limit: 2 };
  const tailors = q.tailored_versions || { used: 0, limit: 2 };
  const exports_ = q.exports || { used: 0, limit: 2 };
  const extraCredits = q.extra_credits || 0;

  // Topbar quick quota badge
  if ($("#quickFitsUsage")) $("#quickFitsUsage").textContent = `${fits.used}/${fits.limit}`;
  if ($("#quickTailorUsage")) $("#quickTailorUsage").textContent = `${tailors.used}/${tailors.limit}`;
  if ($("#quickExportUsage")) $("#quickExportUsage").textContent = `${exports_.used}/${exports_.limit}`;

  // Dashboard quotas
  if ($("#dashFitsUsage")) $("#dashFitsUsage").textContent = `${fits.used} / ${fits.limit}`;
  if ($("#dashFitsBar")) $("#dashFitsBar").style.width = `${Math.min(100, Math.round((fits.used / (fits.limit || 1)) * 100))}%`;
  if ($("#dashTailorsUsage")) $("#dashTailorsUsage").textContent = `${tailors.used} / ${tailors.limit}`;
  if ($("#dashTailorsBar")) $("#dashTailorsBar").style.width = `${Math.min(100, Math.round((tailors.used / (tailors.limit || 1)) * 100))}%`;
  if ($("#dashExportsUsage")) $("#dashExportsUsage").textContent = `${exports_.used} / ${exports_.limit}`;
  if ($("#dashExportsBar")) $("#dashExportsBar").style.width = `${Math.min(100, Math.round((exports_.used / (exports_.limit || 1)) * 100))}%`;

  // Billing tab: Quota cards
  if ($("#quotaFitsText")) $("#quotaFitsText").textContent = `${fits.used} / ${fits.limit}`;
  if ($("#quotaFitsBar")) $("#quotaFitsBar").style.width = `${Math.min(100, Math.round((fits.used / (fits.limit || 1)) * 100))}%`;
  if ($("#quotaTailorsText")) $("#quotaTailorsText").textContent = `${tailors.used} / ${tailors.limit}`;
  if ($("#quotaTailorsBar")) $("#quotaTailorsBar").style.width = `${Math.min(100, Math.round((tailors.used / (tailors.limit || 1)) * 100))}%`;
  if ($("#quotaExportsText")) $("#quotaExportsText").textContent = `${exports_.used} / ${exports_.limit}`;
  if ($("#quotaExportsBar")) $("#quotaExportsBar").style.width = `${Math.min(100, Math.round((exports_.used / (exports_.limit || 1)) * 100))}%`;
  if ($("#quotaExtraCreditsText")) $("#quotaExtraCreditsText").textContent = extraCredits;
  if ($("#quotaResetDate")) $("#quotaResetDate").textContent = data.quota_resets_at || "1st of next month";

  // Section 1: Your Plan Details
  const planName = sub.plan_name || "FREE";
  const subStatus = (sub.status || "ACTIVE").toUpperCase();

  // Header plan badge
  if ($("#billingCurrentPlanBadge")) {
    let badgeText = "FREE";
    if (planName === "PRO_TRIAL" || sub.is_trial) badgeText = "7-DAY TRIAL";
    else if (planName === "PRO_ANNUAL") badgeText = "PRO ANNUAL";
    else if (planName === "PRO_MONTHLY" || planName === "PRO") badgeText = "PRO";
    $("#billingCurrentPlanBadge").textContent = badgeText;
  }

  // Friendly Plan Name
  if ($("#billingPlanNameText")) {
    let friendlyName = "Free Plan";
    if (planName === "PRO_TRIAL" || sub.is_trial) friendlyName = "7-Day Pro Trial";
    else if (planName === "PRO_ANNUAL") friendlyName = "Pro Annual";
    else if (planName === "PRO_MONTHLY" || planName === "PRO") friendlyName = "Pro Monthly";
    $("#billingPlanNameText").textContent = friendlyName;
  }

  // Status Badge
  if ($("#billingStatusBadge")) {
    $("#billingStatusBadge").textContent = subStatus;
    $("#billingStatusBadge").className = "badge-status";
    const statusClass = subStatus.toLowerCase().replace(/_/g, "-");
    $("#billingStatusBadge").classList.add(statusClass);
  }

  // Recurring Amount
  if ($("#billingRecurringAmountText")) {
    const amt = sub.recurring_amount || 0;
    const curr = sub.currency === "USD" ? "$" : "₹";
    if (amt <= 0 || planName === "FREE" || sub.is_trial) {
      $("#billingRecurringAmountText").textContent = "₹0 / month";
    } else {
      const freq = sub.billing_frequency === "annual" ? "year" : "month";
      $("#billingRecurringAmountText").textContent = `${curr}${amt} / ${freq}`;
    }
  }

  // Next Renewal / Expiry
  if ($("#billingNextRenewalText")) {
    if (subStatus === "ENDING" || subStatus === "CANCELLED") {
      $("#billingNextRenewalText").textContent = sub.next_renewal_date ? `Access ends ${sub.next_renewal_date}` : "None (Cancelled)";
    } else if (subStatus === "EXPIRED") {
      $("#billingNextRenewalText").textContent = "Expired";
    } else if (sub.next_renewal_date) {
      $("#billingNextRenewalText").textContent = sub.next_renewal_date;
    } else {
      $("#billingNextRenewalText").textContent = "--";
    }
  }

  // Payment Method text
  if ($("#billingPaymentMethodText")) {
    $("#billingPaymentMethodText").textContent = sub.payment_method_detail || (sub.payment_method_type === "upi" ? "UPI AutoPay" : sub.payment_method_type === "card" ? "Card" : "None");
  }

  // Subscription Alerts
  const endingAlert = $("#subEndingAlert");
  if (endingAlert) {
    if (subStatus === "ENDING" || (sub.cancellation_scheduled && subStatus !== "EXPIRED")) {
      endingAlert.classList.remove("hidden");
      if ($("#subEndingDate")) $("#subEndingDate").textContent = sub.next_renewal_date || "end of billing cycle";
    } else {
      endingAlert.classList.add("hidden");
    }
  }

  const failedAlert = $("#subPaymentFailedAlert");
  if (failedAlert) {
    if (subStatus === "PAYMENT_FAILED" || subStatus === "PAST_DUE" || sub.last_payment_error) {
      failedAlert.classList.remove("hidden");
    } else {
      failedAlert.classList.add("hidden");
    }
  }

  // Section 5: Payment-Method-Aware Subscription Management
  const upiCard = $("#manageUpiCard");
  const cardBox = $("#manageCardBox");
  const freeBox = $("#manageFreeBox");

  const methodType = sub.payment_method_type || "none";
  const isPaidActive = (planName !== "FREE" && !sub.is_trial && subStatus !== "EXPIRED");

  if (upiCard) upiCard.classList.add("hidden");
  if (cardBox) cardBox.classList.add("hidden");
  if (freeBox) freeBox.classList.add("hidden");

  if (isPaidActive && methodType === "upi") {
    if (upiCard) {
      upiCard.classList.remove("hidden");
      if ($("#upiAppLabel")) {
        $("#upiAppLabel").textContent = sub.upi_app ? `Authorized in ${sub.upi_app}` : (sub.payment_method_detail || "Authorized in UPI App");
      }
    }
  } else if (isPaidActive && methodType === "card") {
    if (cardBox) {
      cardBox.classList.remove("hidden");
      if ($("#cardDetailsLabel")) {
        $("#cardDetailsLabel").textContent = sub.payment_method_detail || "Card ending ****4242";
      }
      const cancelBtn = $("#cancelCardRenewalBtn");
      if (cancelBtn) {
        if (sub.cancellation_scheduled || subStatus === "ENDING" || subStatus === "CANCELLED") {
          cancelBtn.disabled = true;
          cancelBtn.innerHTML = `<i data-lucide="check-circle"></i><span>Renewal Cancelled</span>`;
        } else {
          cancelBtn.disabled = false;
          cancelBtn.innerHTML = `<i data-lucide="x-circle"></i><span>Cancel Renewal</span>`;
        }
      }
    }
  } else {
    if (freeBox) {
      freeBox.classList.remove("hidden");
      const p = freeBox.querySelector("p");
      if (p) {
        if (sub.is_trial && subStatus === "TRIAL") {
          p.textContent = `You are on the 7-Day Pro Trial (access until ${sub.next_renewal_date || "trial end"}). No recurring charges or payment mandates exist.`;
        } else if (subStatus === "EXPIRED") {
          p.textContent = "Your previous plan has expired. You are currently on the Free tier with standard quotas.";
        } else {
          p.textContent = "You are currently on the Free plan. No recurring payment mandates or cards are linked.";
        }
      }
    }
  }

  // Active Plan Buttons toggle
  if ($("#freePlanBtn")) {
    $("#freePlanBtn").textContent = (planName === "FREE" && !sub.is_trial) ? "Current Active Plan" : "Free Plan";
    $("#freePlanBtn").disabled = (planName === "FREE" && !sub.is_trial);
  }
  if ($("#startTrialBtn")) {
    if (sub.is_trial || planName === "PRO_TRIAL") {
      $("#startTrialBtn").disabled = true;
      $("#startTrialBtn").innerHTML = `<i data-lucide="check"></i><span>Trial Active</span>`;
    } else if (planName !== "FREE") {
      $("#startTrialBtn").disabled = true;
      $("#startTrialBtn").innerHTML = `<span>Included in Pro</span>`;
    } else {
      $("#startTrialBtn").disabled = false;
      $("#startTrialBtn").innerHTML = `<i data-lucide="sparkles"></i><span>Start 7-Day Pro Trial (₹0)</span>`;
    }
  }
  if ($("#upgradeProBtn")) {
    if (planName === "PRO_MONTHLY" && subStatus === "ACTIVE") {
      $("#upgradeProBtn").disabled = true;
      $("#upgradeProBtn").textContent = "Current Active Plan";
    } else {
      $("#upgradeProBtn").disabled = false;
      $("#upgradeProBtn").innerHTML = `<i data-lucide="zap"></i><span>Upgrade to Pro</span>`;
    }
  }
  if ($("#upgradeAnnualBtn")) {
    if (planName === "PRO_ANNUAL" && subStatus === "ACTIVE") {
      $("#upgradeAnnualBtn").disabled = true;
      $("#upgradeAnnualBtn").textContent = "Current Active Plan";
    } else {
      $("#upgradeAnnualBtn").disabled = false;
      $("#upgradeAnnualBtn").textContent = "Get Pro Annual";
    }
  }

  drawIcons();
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
  if (!tbody) return;
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

async function handleCancelCardRenewal() {
  if (!confirm("Cancel recurring renewal? You will retain Pro access until the end of your current billing period, after which no further charges will occur.")) return;
  const btn = $("#cancelCardRenewalBtn");
  setButtonLoading(btn, true, "Cancelling...");
  try {
    const res = await API.request("/payments/cancel", { method: "POST" });
    toast(res.message || "Renewal cancelled. Your Pro access remains active until the end of your billing cycle.", "success");
    state.user = await API.request("/users/profile");
    renderUserBar();
    await loadBillingSummary();
    await loadPaymentHistory();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Cancel Renewal");
  }
}

async function handleRetryPayment() {
  const btn = $("#retryPaymentBtn");
  setButtonLoading(btn, true, "Retrying...");
  try {
    const res = await API.request("/payments/retry-failed", { method: "POST" });
    toast(res.message || "Payment status refreshed successfully.", "success");
    await loadBillingSummary();
    await loadPaymentHistory();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    setButtonLoading(btn, false, "Retry Payment");
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
        "Evaluated across 10 essential criteria. Every score is explainable with concrete recommendations.";
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

let onboardingState = {
  step: 1,
  goal: "new_job",
  method: "upload",
  draft: null,
};

function resetOnboardingWizard() {
  onboardingState = {
    step: 1,
    goal: "new_job",
    method: "upload",
    draft: null,
  };
  $$(".onboarding-option-card[data-goal]").forEach(card => {
    card.classList.toggle("selected", card.dataset.goal === "new_job");
  });
  $$(".onboarding-option-card[data-method]").forEach(card => {
    card.classList.toggle("selected", card.dataset.method === "upload");
  });
  const uploadZone = $("#onboardUploadZone");
  if (uploadZone) uploadZone.classList.remove("hidden");
  const uploadProgress = $("#onboardUploadProgress");
  if (uploadProgress) uploadProgress.classList.add("hidden");
  const fileChosen = $("#onboardFileChosenName");
  if (fileChosen) {
    fileChosen.textContent = "";
    fileChosen.classList.add("hidden");
  }
  const fileInput = $("#onboardFileInput");
  if (fileInput) fileInput.value = "";

  renderOnboardingStep(1);
}

function renderOnboardingStep(step) {
  onboardingState.step = step;

  // 1. Stepper pills
  $$("#onboardingStepper .onboarding-step-pill").forEach((pill) => {
    const s = parseInt(pill.dataset.step, 10);
    pill.classList.remove("active", "completed");
    if (s === step) pill.classList.add("active");
    else if (s < step) pill.classList.add("completed");
  });
  $$("#onboardingStepper .onboarding-step-divider").forEach((divider, idx) => {
    divider.classList.toggle("completed", idx + 1 < step);
  });

  // 2. Toggle panels
  for (let i = 1; i <= 5; i++) {
    const panel = $(`#onboardStep${i}`);
    if (panel) panel.classList.toggle("hidden", i !== step);
  }

  // 3. Footer buttons
  const backBtn = $("#onboardBackBtn");
  const nextBtn = $("#onboardNextBtn");
  const skipBtn = $("#onboardSkipBtn");
  const footer = $("#onboardModalFooter");

  if (step === 1) {
    if (backBtn) backBtn.classList.add("hidden");
    if (skipBtn) skipBtn.classList.add("hidden");
    if (nextBtn) {
      nextBtn.classList.remove("hidden");
      nextBtn.innerHTML = `<span>Continue &rarr;</span>`;
    }
    if (footer) footer.classList.remove("hidden");
  } else if (step === 2) {
    if (backBtn) backBtn.classList.remove("hidden");
    if (skipBtn) skipBtn.classList.add("hidden");
    if (nextBtn) {
      nextBtn.classList.remove("hidden");
      nextBtn.innerHTML = `<span>Continue &rarr;</span>`;
    }
    if (footer) footer.classList.remove("hidden");
  } else if (step === 3) {
    if (backBtn) backBtn.classList.remove("hidden");
    if (skipBtn) skipBtn.classList.add("hidden");
    if (nextBtn) {
      nextBtn.classList.remove("hidden");
      nextBtn.innerHTML = `<span>Looks Good, Continue &rarr;</span>`;
    }
    if (footer) footer.classList.remove("hidden");
  } else if (step === 4) {
    if (backBtn) backBtn.classList.remove("hidden");
    if (skipBtn) skipBtn.classList.remove("hidden");
    if (nextBtn) {
      nextBtn.classList.remove("hidden");
      nextBtn.innerHTML = `<span>Save & Generate Resume &rarr;</span>`;
    }
    if (footer) footer.classList.remove("hidden");
  } else if (step === 5) {
    if (footer) footer.classList.add("hidden");
  }
  drawIcons();
}

function checkAndShowOnboarding() {
  const seen = localStorage.getItem("smartresume_seen_onboarding");
  const p = state.profile;
  const isFresh = !p || ((!p.experiences || p.experiences.length === 0) && (!p.skills || p.skills.length === 0));
  if (!seen && isFresh) {
    const modal = $("#onboardingModal");
    if (modal) {
      modal.classList.remove("hidden");
      resetOnboardingWizard();
    }
  }
}

function wireOnboardingModal() {
  // Step 1: Goal selection
  $$(".onboarding-option-card[data-goal]").forEach((card) => {
    card.addEventListener("click", () => {
      $$(".onboarding-option-card[data-goal]").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      onboardingState.goal = card.dataset.goal;
    });
  });

  // Step 2: Method selection
  $$(".onboarding-option-card[data-method]").forEach((card) => {
    card.addEventListener("click", () => {
      $$(".onboarding-option-card[data-method]").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      onboardingState.method = card.dataset.method;
      const uploadZone = $("#onboardUploadZone");
      if (uploadZone) {
        uploadZone.classList.toggle("hidden", card.dataset.method !== "upload");
      }
    });
  });

  // Step 2: File upload handling
  const fileInput = $("#onboardFileInput");
  const uploadZone = $("#onboardUploadZone");

  async function handleOnboardingFileUpload(file) {
    if (!file) return;
    const progress = $("#onboardUploadProgress");
    const statusText = $("#onboardUploadStatusText");
    if (progress) progress.classList.remove("hidden");
    if (uploadZone) uploadZone.classList.add("hidden");
    if (statusText) statusText.textContent = "Reading your resume and organizing your experience...";

    try {
      const formData = new FormData();
      formData.append("file", file);
      const draft = await API.request("/profile/import/parse-file", { method: "POST", body: formData });
      onboardingState.draft = draft;

      if ($("#onboardNameInput")) $("#onboardNameInput").value = state.user?.name || draft.full_name || "";
      if ($("#onboardTitleInput")) $("#onboardTitleInput").value = draft.headline || "";
      if ($("#onboardContactInput")) $("#onboardContactInput").value = draft.phone || state.user?.email || "";
      if ($("#onboardRecentExpInput")) {
        const topExp = draft.experiences?.[0];
        $("#onboardRecentExpInput").value = topExp ? `${topExp.role_title} at ${topExp.company}` : "";
      }
      if ($("#onboardSkillsInput")) {
        $("#onboardSkillsInput").value = (draft.skills || []).map(s => typeof s === "string" ? s : s.name).slice(0, 8).join(", ");
      }
      if ($("#onboardLocationInput")) $("#onboardLocationInput").value = draft.location || "";

      toast("Resume extracted! Please review your details.");
      renderOnboardingStep(3);
    } catch (err) {
      toast(err.message || "Failed to parse resume file.", "error");
      if (uploadZone) uploadZone.classList.remove("hidden");
      if (progress) progress.classList.add("hidden");
    }
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) handleOnboardingFileUpload(file);
    });
  }

  if (uploadZone) {
    uploadZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadZone.classList.add("dragover");
    });
    uploadZone.addEventListener("dragleave", () => {
      uploadZone.classList.remove("dragover");
    });
    uploadZone.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadZone.classList.remove("dragover");
      const file = e.dataTransfer.files?.[0];
      if (file) handleOnboardingFileUpload(file);
    });
  }

  // Navigation Buttons
  $("#onboardBackBtn")?.addEventListener("click", () => {
    if (onboardingState.step > 1) {
      renderOnboardingStep(onboardingState.step - 1);
    }
  });

  $("#onboardNextBtn")?.addEventListener("click", async () => {
    if (onboardingState.step === 1) {
      renderOnboardingStep(2);
    } else if (onboardingState.step === 2) {
      if (onboardingState.method === "upload") {
        if (fileInput && fileInput.files?.length) {
          handleOnboardingFileUpload(fileInput.files[0]);
        } else {
          toast("Please select a resume file or choose 'Start from scratch'.", "info");
        }
      } else {
        if ($("#onboardNameInput")) $("#onboardNameInput").value = state.user?.name || "";
        if ($("#onboardContactInput")) $("#onboardContactInput").value = state.user?.email || "";
        renderOnboardingStep(3);
      }
    } else if (onboardingState.step === 3) {
      renderOnboardingStep(4);
    } else if (onboardingState.step === 4) {
      await saveOnboardingProfile();
    }
  });

  $("#onboardSkipBtn")?.addEventListener("click", async () => {
    await saveOnboardingProfile();
  });

  async function saveOnboardingProfile() {
    const nextBtn = $("#onboardNextBtn");
    setButtonLoading(nextBtn, true, "Saving...");
    try {
      if (onboardingState.draft) {
        const payload = {
          ...onboardingState.draft,
          headline: $("#onboardTitleInput")?.value || onboardingState.draft.headline || "",
          location: $("#onboardLocationInput")?.value || onboardingState.draft.location || "",
          phone: $("#onboardContactInput")?.value || onboardingState.draft.phone || "",
        };
        await API.request("/profile/import/commit", { method: "POST", body: payload });
      } else {
        const skillsArr = ($("#onboardSkillsInput")?.value || "")
          .split(",")
          .map(s => s.trim())
          .filter(Boolean)
          .map(s => ({ name: s, category: "TECHNICAL" }));
        const expsArr = [];
        const expStr = $("#onboardRecentExpInput")?.value?.trim();
        if (expStr) {
          const parts = expStr.split(/ at | @ /i);
          expsArr.push({
            role_title: parts[0] || expStr,
            company: parts[1] || "Company",
            start_date: "2023-01",
            end_date: null,
            is_current: true,
          });
        }
        const draftPayload = {
          headline: $("#onboardTitleInput")?.value || "",
          location: $("#onboardLocationInput")?.value || "",
          phone: $("#onboardContactInput")?.value || "",
          skills: skillsArr,
          experiences: expsArr,
        };
        await API.request("/profile/import/commit", { method: "POST", body: draftPayload });
      }

      localStorage.setItem("smartresume_seen_onboarding", "true");
      await loadMasterProfile();
      renderDashboard();
      renderOnboardingStep(5);
    } catch (err) {
      toast(err.message || "Unable to save profile info.", "error");
    } finally {
      setButtonLoading(nextBtn, false, "Save & Generate Resume \u2192");
    }
  }

  // Step 5 Actions
  $("#onboardFinishBuilderBtn")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
    navigateToTab("resume-builder");
  });

  $("#onboardFinishMatchBtn")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
    navigateToTab("fit");
  });

  $("#closeOnboardingModalBtn")?.addEventListener("click", () => {
    localStorage.setItem("smartresume_seen_onboarding", "true");
    $("#onboardingModal")?.classList.add("hidden");
  });

  // Legacy compatibility bindings
  $("#dismissOnboardingBtn")?.addEventListener("click", () => {
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
  });
}
window.resetOnboardingWizard = resetOnboardingWizard;

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
      toast(res.message || "Synced items into Achievement Proof.");
      await loadEvidenceVault();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false, "Sync from Career Profile");
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
// 4. INTERVIEW COPILOT MODULE — TEXT & LIVE AI MODES
// ==========================================================================
let activeInterviewSessionId = null;
let liveMediaStream = null;
let isLiveMicMuted = false;
let isLiveCameraOff = false;

// Active job application context (propagate across tabs)
if (!state.activeJobContext) {
  state.activeJobContext = {
    role: "Software Engineer",
    company: "Target Company",
    companyUrl: "",
    jobUrl: "",
    versionId: null,
    jobId: null,
    verification: null,
  };
}

function syncInterviewContextUI() {
  const ctx = state.activeJobContext || {};
  const roleEl = $("#interviewActiveRole");
  const compEl = $("#interviewActiveCompany");
  const roleInp = $("#interviewRoleInput");
  const compInp = $("#interviewCompanyInput");

  if (roleEl && ctx.role) roleEl.textContent = ctx.role;
  if (compEl && ctx.company) compEl.textContent = ctx.company;
  if (roleInp && ctx.role) roleInp.value = ctx.role;
  if (compInp && ctx.company) compInp.value = ctx.company;

  if (ctx.company) {
    verifyCompanyContext(ctx.company, ctx.companyUrl, ctx.jobUrl);
  }
}

async function verifyCompanyContext(companyName, companyUrl = "", jobUrl = "") {
  if (!companyName) return;
  const badge = $("#interviewCompanyBadge");
  try {
    const res = await API.request("/company/verify", {
      method: "POST",
      body: {
        company_name: companyName,
        company_url: companyUrl || null,
        job_url: jobUrl || null,
      },
    });
    if (badge) {
      if (res.verification_status === "VERIFIED") {
        badge.textContent = "✓ Verified";
        badge.className = "company-badge badge-verified";
      } else if (res.verification_status === "LIKELY_VERIFIED") {
        badge.textContent = "✓ Likely Verified";
        badge.className = "company-badge badge-likely";
      } else if (res.verification_status === "SUSPICIOUS") {
        badge.textContent = "⚠ Needs Review";
        badge.className = "company-badge badge-suspicious";
      } else {
        badge.textContent = "? Unverified";
        badge.className = "company-badge badge-unverified";
      }
    }
    state.activeJobContext.verification = res;
  } catch (_) {}
}

async function loadClaimsToDefend() {
  const container = $("#claimsList");
  if (!container) return;
  try {
    const jobId = state.activeJobContext?.jobId || "";
    const claims = await API.request(`/interview/claims-to-defend?job_id=${jobId}`);
    if (!claims || claims.length === 0) {
      container.innerHTML = `<p class="text-xs text-muted">Complete your career profile to generate grounded claims to defend.</p>`;
      return;
    }
    container.innerHTML = claims.slice(0, 3).map((c) => `
      <div class="claim-item-card">
        <div class="claim-head">
          <span class="badge-sub">${escapeHtml(c.category || "Technical")}</span>
          <strong>${escapeHtml(c.claim)}</strong>
        </div>
        <p class="text-xs text-muted mt-1">${escapeHtml(c.why_asked)}</p>
        <div class="claim-prep-tip text-xs">
          <strong>Prep Question:</strong> "${escapeHtml(c.suggested_question)}"
        </div>
      </div>
    `).join("");
  } catch (_) {}
}

function stopLiveInterviewMedia() {
  if (liveMediaStream) {
    liveMediaStream.getTracks().forEach((track) => track.stop());
    liveMediaStream = null;
  }
  const videoEl = $("#liveCameraPreview");
  if (videoEl) videoEl.srcObject = null;
  isLiveMicMuted = false;
  isLiveCameraOff = false;
  $("#cameraDisabledOverlay")?.classList.add("hidden");
  $("#liveMicToggleBtn")?.classList.remove("active-muted");
}

function wireInterviewCopilot() {
  // Context edit toggle
  $("#interviewEditContextBtn")?.addEventListener("click", () => {
    const row = $("#interviewContextInputsRow");
    if (row) row.classList.toggle("hidden");
  });

  // Role and Company manual inputs
  $("#interviewRoleInput")?.addEventListener("input", (e) => {
    const val = e.target.value.trim() || "Software Engineer";
    state.activeJobContext.role = val;
    if ($("#interviewActiveRole")) $("#interviewActiveRole").textContent = val;
  });

  $("#interviewCompanyInput")?.addEventListener("change", (e) => {
    const val = e.target.value.trim() || "Target Company";
    state.activeJobContext.company = val;
    if ($("#interviewActiveCompany")) $("#interviewActiveCompany").textContent = val;
    verifyCompanyContext(val);
  });

  $("#interviewResetContextBtn")?.addEventListener("click", () => {
    state.activeJobContext = {
      role: "Software Engineer",
      company: "Target Company",
      companyUrl: "",
      jobUrl: "",
      versionId: null,
      jobId: null,
      verification: null,
    };
    syncInterviewContextUI();
    toast("Interview context reset.");
  });

  // Mode selection cards
  const modeTextCard = $("#modeCardText");
  const modeLiveCard = $("#modeCardLive");

  modeTextCard?.addEventListener("click", () => {
    modeTextCard.classList.add("active-card");
    modeLiveCard?.classList.remove("active-card");
  });

  modeLiveCard?.addEventListener("click", () => {
    modeLiveCard.classList.add("active-card");
    modeTextCard?.classList.remove("active-card");
  });

  // START TEXT INTERVIEW
  $("#startTextInterviewBtn")?.addEventListener("click", async () => {
    const role = $("#interviewRoleInput")?.value.trim() || state.activeJobContext.role || "Software Engineer";
    const company = $("#interviewCompanyInput")?.value.trim() || state.activeJobContext.company || "Target Company";
    const level = $("#interviewCareerLevelSelect")?.value || "DEVELOPING";
    const difficulty = $("#interviewDifficultySelect")?.value || "MEDIUM";
    const practice_mode = $("#interviewPracticeModeSelect")?.value || "STANDARD_20";

    try {
      toast("Initializing Interview Practice Session...");
      const session = await API.request("/interview/sessions", {
        method: "POST",
        body: {
          target_role: role,
          target_company: company,
          session_mode: "TEXT",
          career_level: level,
          difficulty: difficulty,
          practice_mode: practice_mode,
          job_id: state.activeJobContext.jobId || null,
        },
      });

      activeInterviewSessionId = session.id;
      $("#textInterviewWorkspace")?.classList.remove("hidden");
      $("#liveInterviewRoom")?.classList.add("hidden");
      $("#interviewReviewCard")?.classList.add("hidden");
      $("#turnEvaluationDrawer")?.classList.add("hidden");

      renderActiveInterviewSession(session);
      await loadInterviewSessions();
      toast(`Level 1 initialized (${difficulty} difficulty).`);
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // TEXT INTERVIEW TURN SUBMIT
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

      // Render Turn-by-Turn feedback
      if (turnRes.turn_feedback) {
        const tf = turnRes.turn_feedback;
        const drawer = $("#turnEvaluationDrawer");
        const content = $("#turnEvaluationContent");
        const status = $("#turnEvaluationStatus");
        if (drawer && content) {
          drawer.classList.remove("hidden");
          const qType = tf.question_type || "Follow-up Question";
          if (status) status.textContent = qType.replace(/_/g, " ");

          let html = "";
          if (tf.strong) {
            html += `<div class="eval-tag strong"><strong>Strong:</strong> ${escapeHtml(tf.strong)}</div>`;
          }
          if (tf.weak) {
            html += `<div class="eval-tag weak"><strong>Gap:</strong> ${escapeHtml(tf.weak)}</div>`;
          }
          if (tf.improve) {
            html += `<div class="eval-tag improve"><strong>Improve:</strong> ${escapeHtml(tf.improve)}</div>`;
          }
          content.innerHTML = html;
        }

        // Update progression step active indicator
        if (tf.level) {
          const lvl = tf.level;
          $$(".prog-step").forEach((step, idx) => {
            if (idx + 1 === lvl) step.classList.add("active");
            else step.classList.remove("active");
          });
          const pill = $("#interviewStatusPill");
          if (pill) pill.textContent = `Level ${lvl} / 6`;
        }

        if (tf.star_assessment) {
          toast(tf.star_assessment);
        }
      }
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // COMPLETE & EVALUATE INTERVIEW
  $("#endInterviewBtn")?.addEventListener("click", async () => {
    if (!activeInterviewSessionId) return;
    try {
      toast("Generating Evidence-Based Interview Review...");
      const evaluation = await API.request(`/interview/sessions/${activeInterviewSessionId}/complete`, { method: "POST" });

      $("#textInterviewWorkspace")?.classList.add("hidden");
      $("#liveInterviewRoom")?.classList.add("hidden");
      stopLiveInterviewMedia();

      renderInterviewReviewCard(evaluation);
      toast("Review generated!");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  // START LIVE AI INTERVIEW
  $("#startLiveInterviewBtn")?.addEventListener("click", async () => {
    const role = $("#interviewRoleInput")?.value.trim() || state.activeJobContext.role || "Software Engineer";
    const company = $("#interviewCompanyInput")?.value.trim() || state.activeJobContext.company || "Target Company";
    const level = $("#interviewCareerLevelSelect")?.value || "DEVELOPING";

    const room = $("#liveInterviewRoom");
    const notConfiguredBanner = $("#liveNotConfiguredBanner");
    const statusPill = $("#liveConnectionStatus");

    // Hide other panels
    $("#textInterviewWorkspace")?.classList.add("hidden");
    $("#interviewReviewCard")?.classList.add("hidden");
    if (room) room.classList.remove("hidden");

    if ($("#liveRoleCompany")) {
      $("#liveRoleCompany").textContent = `${role} at ${company}`;
    }

    try {
      toast("Checking Gemini Live configuration...");
      const liveConfig = await API.request("/interview/live-config");

      if (!liveConfig.configured) {
        if (notConfiguredBanner) notConfiguredBanner.classList.remove("hidden");
        if (statusPill) {
          statusPill.textContent = "Config Pending";
          statusPill.className = "badge-sub badge-unverified";
        }
        return;
      }

      if (notConfiguredBanner) notConfiguredBanner.classList.add("hidden");
      if (statusPill) {
        statusPill.textContent = "Connecting...";
        statusPill.className = "badge-sub badge-likely";
      }

      // Explicit permission request for camera & mic
      toast("Requesting camera and microphone access...");
      liveMediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      const videoEl = $("#liveCameraPreview");
      if (videoEl) {
        videoEl.srcObject = liveMediaStream;
      }

      if (statusPill) {
        statusPill.textContent = "Live Active";
        statusPill.className = "badge-sub badge-verified";
      }

      // Create live session in backend
      const session = await API.request("/interview/sessions", {
        method: "POST",
        body: {
          target_role: role,
          target_company: company,
          session_mode: "LIVE",
          career_level: level,
          job_id: state.activeJobContext.jobId || null,
        },
      });
      activeInterviewSessionId = session.id;
      toast("Live Interview session ready. AI interviewer listening.");
    } catch (err) {
      if (statusPill) {
        statusPill.textContent = "Access Denied / Interrupted";
        statusPill.className = "badge-sub badge-suspicious";
      }
      toast(err.message || "Could not access camera/microphone.", "error");
    }
  });

  // LIVE INTERVIEW CONTROLS
  $("#liveMicToggleBtn")?.addEventListener("click", () => {
    if (!liveMediaStream) return;
    const audioTracks = liveMediaStream.getAudioTracks();
    if (audioTracks.length > 0) {
      isLiveMicMuted = !isLiveMicMuted;
      audioTracks.forEach((t) => (t.enabled = !isLiveMicMuted));
      const btn = $("#liveMicToggleBtn");
      if (btn) {
        if (isLiveMicMuted) {
          btn.classList.add("active-muted");
          btn.querySelector(".control-label").textContent = "Unmute";
        } else {
          btn.classList.remove("active-muted");
          btn.querySelector(".control-label").textContent = "Mute";
        }
      }
    }
  });

  $("#liveCameraToggleBtn")?.addEventListener("click", () => {
    if (!liveMediaStream) return;
    const videoTracks = liveMediaStream.getVideoTracks();
    if (videoTracks.length > 0) {
      isLiveCameraOff = !isLiveCameraOff;
      videoTracks.forEach((t) => (t.enabled = !isLiveCameraOff));
      const overlay = $("#cameraDisabledOverlay");
      if (overlay) {
        if (isLiveCameraOff) overlay.classList.remove("hidden");
        else overlay.classList.add("hidden");
      }
    }
  });

  $("#liveRepeatBtn")?.addEventListener("click", () => {
    toast("Repeating question...");
  });

  $("#liveSkipBtn")?.addEventListener("click", () => {
    toast("Skipping to next round...");
  });

  $("#liveEndBtn")?.addEventListener("click", async () => {
    stopLiveInterviewMedia();
    $("#liveInterviewRoom")?.classList.add("hidden");
    if (activeInterviewSessionId) {
      try {
        const evalRes = await API.request(`/interview/sessions/${activeInterviewSessionId}/complete`, { method: "POST" });
        renderInterviewReviewCard(evalRes);
      } catch (_) {}
    }
    toast("Live interview ended.");
  });

  // Review Practice Again
  $("#reviewPracticeAgainBtn")?.addEventListener("click", () => {
    $("#interviewReviewCard")?.classList.add("hidden");
    $("#textInterviewWorkspace")?.classList.remove("hidden");
  });

  // Gemini Config Modal controls
  $("#closeGeminiModalBtn")?.addEventListener("click", closeGeminiModal);
  $("#dismissGeminiModalBtn")?.addEventListener("click", closeGeminiModal);
}

function openGeminiConfigModal() {
  const modal = $("#geminiConfigModal");
  if (modal) modal.classList.remove("hidden");
}
window.openGeminiConfigModal = openGeminiConfigModal;

function closeGeminiModal() {
  const modal = $("#geminiConfigModal");
  if (modal) modal.classList.add("hidden");
}
window.closeGeminiModal = closeGeminiModal;

function renderInterviewReviewCard(evaluation) {
  const card = $("#interviewReviewCard");
  if (!card) return;
  card.classList.remove("hidden");

  const badge = $("#reviewReadinessBadge");
  if (badge) {
    badge.textContent = evaluation.readiness_level || "COMPLETED";
    badge.className = evaluation.readiness_level === "READY" ? "badge-musthave" : "badge-sub badge-unverified";
  }

  // 6-Dimension Score Grid
  if ($("#reportOverallScore")) $("#reportOverallScore").textContent = evaluation.overall_score !== undefined ? `${evaluation.overall_score}%` : "--";
  if ($("#reportTechnicalScore")) $("#reportTechnicalScore").textContent = evaluation.technical_score !== undefined ? `${evaluation.technical_score}%` : "--";
  if ($("#reportProblemSolvingScore")) $("#reportProblemSolvingScore").textContent = evaluation.problem_solving_score !== undefined ? `${evaluation.problem_solving_score}%` : "--";
  if ($("#reportCommunicationScore")) $("#reportCommunicationScore").textContent = evaluation.communication_score !== undefined ? `${evaluation.communication_score}%` : "--";
  if ($("#reportResumeKnowledgeScore")) $("#reportResumeKnowledgeScore").textContent = evaluation.resume_knowledge_score !== undefined ? `${evaluation.resume_knowledge_score}%` : "--";
  if ($("#reportRoleReadinessScore")) $("#reportRoleReadinessScore").textContent = evaluation.role_readiness_score !== undefined ? `${evaluation.role_readiness_score}%` : "--";

  // What Is Holding You Back
  const holdBox = $("#reportHoldingBackContainer");
  const holdText = $("#reportHoldingBackText");
  if (holdBox && holdText) {
    if (evaluation.holding_back) {
      holdText.textContent = evaluation.holding_back;
      holdBox.classList.remove("hidden");
    } else {
      holdBox.classList.add("hidden");
    }
  }

  // Next Best Practice Recommendation
  const nextBox = $("#reportNextPracticeContainer");
  const nextText = $("#reportNextPracticeText");
  if (nextBox && nextText) {
    if (evaluation.suggested_next_practice) {
      nextText.textContent = evaluation.suggested_next_practice;
      nextBox.classList.remove("hidden");
    } else {
      nextBox.classList.add("hidden");
    }
  }

  const strongList = $("#reviewStrongList");
  if (strongList) {
    strongList.innerHTML = (evaluation.strong_areas || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("");
  }

  const practiceList = $("#reviewPracticeList");
  if (practiceList) {
    practiceList.innerHTML = (evaluation.needs_practice || []).map((p) => `<li>${escapeHtml(p)}</li>`).join("");
  }

  const techGaps = $("#reviewTechnicalGapsList");
  if (techGaps) {
    techGaps.innerHTML = (evaluation.technical_gaps || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("");
  }

  const claimsList = $("#reviewClaimsList");
  if (claimsList) {
    claimsList.innerHTML = (evaluation.resume_claims_to_defend || []).map((c) => `
      <li><strong>${escapeHtml(c.claim || "Claim")}:</strong> ${escapeHtml(c.defense_tip || "")}</li>
    `).join("");
  }

  drawIcons();
}

async function loadInterviewSessions() {
  const container = $("#interviewSessionsList");
  if (!container) return;
  try {
    const sessions = await API.request("/interview/sessions");
    if (!sessions || sessions.length === 0) {
      container.innerHTML = `<p class="text-muted text-xs">No previous interview sessions yet.</p>`;
      return;
    }
    container.innerHTML = sessions.map((s) => `
      <div class="panel p-2 mb-2 text-xs cursor-pointer" onclick="resumeInterviewSession(${s.id})">
        <strong>${escapeHtml(s.target_role || "Role")}</strong> at ${escapeHtml(s.target_company || "Company")}
        <div class="flex-between text-muted mt-1">
          <span>${s.session_mode || "TEXT"}</span>
          <span>${s.status}</span>
        </div>
      </div>
    `).join("");
  } catch (_) {}
}

async function resumeInterviewSession(sessionId) {
  try {
    const session = await API.request(`/interview/sessions/${sessionId}`);
    activeInterviewSessionId = session.id;
    $("#textInterviewWorkspace")?.classList.remove("hidden");
    $("#liveInterviewRoom")?.classList.add("hidden");
    $("#interviewReviewCard")?.classList.add("hidden");
    renderActiveInterviewSession(session);
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderActiveInterviewSession(session) {
  if ($("#activeInterviewTitle")) {
    $("#activeInterviewTitle").textContent = `${session.target_role} at ${session.target_company}`;
  }
  if ($("#interviewStatusPill")) {
    $("#interviewStatusPill").textContent = session.status;
  }

  const chatBox = $("#interviewChatBox");
  if (chatBox) {
    chatBox.innerHTML = "";
    (session.messages || []).forEach((m) => {
      appendInterviewMsg(m.sender.toLowerCase() === "user" ? "user" : "ai", m.message_text);
    });
  }
}

function appendInterviewMsg(sender, text) {
  const chatBox = $("#interviewChatBox");
  if (!chatBox) return;
  const msgEl = document.createElement("div");
  msgEl.className = `chat-msg ${sender}`;
  msgEl.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
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
  canvas.innerHTML = `<div class="p-5 text-center text-muted"><i data-lucide="loader"></i><p class="mt-2">Loading template preview...</p></div>`;
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
  "readiness": "Clear alignment score between verified profile qualifications and target job requirements.",
  "coverage": "Percentage of hard and soft job requirements directly matched by your profile evidence.",
  "strong match": "Direct, verified experience or projects proving exact mastery of the required skill or responsibility.",
  "partial match": "Related, transferable background present, but lacking exact technology or keyword match.",
  "missing evidence": "Requirement mentioned in job posting that has zero supporting proof in your profile.",
  "honest gap": "Requirement intentionally excluded from tailoring because you lack verified evidence, protecting against fabrication.",
  "career level": "Seniority tier (Early Career, Developing Professional, Senior, Lead, Executive) based on verified experience years and scope.",
  "tailoring": "Restructuring existing verified achievements to highlight relevance to a specific role without fabricating unverified claims.",
  "version snapshot": "A saved point-in-time copy of your tailored resume locked for export and job submission.",
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
