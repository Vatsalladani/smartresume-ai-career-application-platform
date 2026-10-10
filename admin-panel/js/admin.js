/**
 * SmartResume.ai — Dedicated Admin Console Controller
 * Independent Single-Page Application communicating via authenticated REST APIs.
 */

const STATE_KEY_TOKEN = "smartresume_admin_token";
const STATE_KEY_API = "smartresume_admin_api";
const STATE_KEY_REMEMBER_EMAIL = "smartresume_admin_remembered_email";
const DEFAULT_API_URL = "http://127.0.0.1:8000";

const state = {
  token: localStorage.getItem(STATE_KEY_TOKEN) || "",
  apiBase: (localStorage.getItem(STATE_KEY_API) || DEFAULT_API_URL).replace(/\/+$/, ""),
  adminUser: null,
  activeTab: "overview",
  currentPage: 1,
  userSearchQuery: "",
  latestInvite: null,
};

// UI Helper Utilities
function $(selector) { return document.querySelector(selector); }
function $$(selector) { return document.querySelectorAll(selector); }

function toast(message, type = "info") {
  const container = $("#toastContainer");
  if (!container) return;
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${escapeHtml(message)}</span>`;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 200);
  }, 3500);
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

function renderIcons() {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }
}

// API Request Engine
async function adminApi(endpoint, options = {}) {
  const url = `${state.apiBase}/api/v1${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const err = new Error(data?.message || data?.detail || `API request failed with HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (err) {
    if (err.status === 401 && !endpoint.includes("/login") && !endpoint.includes("/signup")) {
      handleAdminLogout("Session expired. Please sign in again.");
    }
    throw err;
  }
}

// Setup & Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

function initApp() {
  // Sync API URL input with state
  const apiInput = $("#adminApiUrlInput");
  if (apiInput) apiInput.value = state.apiBase;

  const displayEl = $("#apiBaseDisplay");
  if (displayEl) displayEl.textContent = state.apiBase;

  // Restore remembered email
  const remembered = localStorage.getItem(STATE_KEY_REMEMBER_EMAIL);
  const emailInput = $("#adminEmailInput");
  const rememberBox = $("#rememberEmailCheckbox");
  if (remembered && emailInput) {
    emailInput.value = remembered;
    if (rememberBox) rememberBox.checked = true;
  }

  // Environment badge
  updateEnvBadge();

  // Check URL query parameters for invite tokens (e.g. ?token=XYZ&email=...)
  checkUrlForInviteToken();

  // Wire Forms & Buttons
  $("#adminLoginForm")?.addEventListener("submit", handleAdminLogin);
  $("#adminSignupForm")?.addEventListener("submit", handleAdminSignup);
  $("#createInviteForm")?.addEventListener("submit", handleCreateInvitation);
  $("#adminLogoutBtn")?.addEventListener("click", () => handleAdminLogout("Signed out successfully."));
  $("#refreshCurrentViewBtn")?.addEventListener("click", refreshActiveView);
  $("#refreshAuditLogsBtn")?.addEventListener("click", loadAuditLogs);
  $("#switchApiTargetBtn")?.addEventListener("click", promptChangeApiTarget);

  // Wire User Search Input
  let debounceTimeout = null;
  $("#userSearchInput")?.addEventListener("input", (e) => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      state.userSearchQuery = e.target.value.trim();
      loadUsers(1, state.userSearchQuery);
    }, 300);
  });

  // Wire Tab Navigation
  $$(".nav-btn[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      activateTab(btn.dataset.tab);
    });
  });

  // Handle Hash Routing
  window.addEventListener("hashchange", handleHashRouting);

  // Validate existing session
  if (state.token) {
    verifyAdminSession();
  } else {
    showAuthView();
  }
}

function updateEnvBadge() {
  const badge = $("#activeEnvBadge");
  if (!badge) return;
  const isProd = state.apiBase.includes("vercel.app") || state.apiBase.includes("smartresume.ai");
  badge.textContent = isProd ? "PRODUCTION" : "LOCAL DEV";
  badge.className = `badge-env ${isProd ? "badge-danger" : "badge-admin"}`;
}

window.setApiTarget = function(url) {
  const input = $("#adminApiUrlInput");
  if (input) input.value = url;
};

function promptChangeApiTarget() {
  const current = state.apiBase;
  const target = prompt("Enter backend API base URL (e.g., http://127.0.0.1:8000 or https://smartresume-ai-career-application-p.vercel.app):", current);
  if (target && target.trim() && target.trim() !== current) {
    state.apiBase = target.trim().replace(/\/+$/, "");
    localStorage.setItem(STATE_KEY_API, state.apiBase);
    $("#apiBaseDisplay").textContent = state.apiBase;
    updateEnvBadge();
    toast(`API Target updated to ${state.apiBase}`);
    refreshActiveView();
  }
}

// Auth Mode Switching & Password Visibility
window.switchAuthMode = function(mode) {
  const loginForm = $("#adminLoginForm");
  const signupForm = $("#adminSignupForm");
  const tabLogin = $("#tabLoginBtn");
  const tabSignup = $("#tabSignupBtn");
  const errLogin = $("#authErrorMessage");
  const errSignup = $("#signupErrorMessage");

  if (errLogin) errLogin.classList.add("hidden");
  if (errSignup) errSignup.classList.add("hidden");

  if (mode === "signup") {
    loginForm?.classList.add("hidden");
    signupForm?.classList.remove("hidden");
    tabLogin?.classList.remove("active");
    tabSignup?.classList.add("active");
  } else {
    loginForm?.classList.remove("hidden");
    signupForm?.classList.add("hidden");
    tabLogin?.classList.add("active");
    tabSignup?.classList.remove("active");
  }
  renderIcons();
};

window.togglePasswordVisibility = function(inputId, btnEl) {
  const input = $(`#${inputId}`);
  if (!input) return;
  const isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";
  if (btnEl) {
    btnEl.innerHTML = `<i data-lucide="${isPassword ? 'eye-off' : 'eye'}"></i>`;
    renderIcons();
  }
};

function checkUrlForInviteToken() {
  let token = "";
  let email = "";

  // 1. Search params (?token=XYZ&email=...)
  const params = new URLSearchParams(window.location.search);
  if (params.get("token")) {
    token = params.get("token");
    email = params.get("email") || "";
  }

  // 2. Hash params (#/signup?token=XYZ&email=...)
  const hash = window.location.hash;
  if (hash.includes("token=")) {
    const hashQuery = hash.split("?")[1];
    if (hashQuery) {
      const hParams = new URLSearchParams(hashQuery);
      if (hParams.get("token")) {
        token = hParams.get("token");
        email = hParams.get("email") || email;
      }
    }
  }

  if (token) {
    switchAuthMode("signup");
    const tokenInput = $("#adminSignupToken");
    const emailInput = $("#adminSignupEmail");
    if (tokenInput) tokenInput.value = token;
    if (emailInput && email) emailInput.value = email;
    toast("Administrator invitation token loaded from link.", "info");
  } else if (window.location.hash.startsWith("#/signup")) {
    switchAuthMode("signup");
  }
}

// Authentication Handlers
async function handleAdminLogin(e) {
  e.preventDefault();
  const identifier = $("#adminEmailInput")?.value.trim();
  const password = $("#adminPasswordInput")?.value;
  const apiUrl = $("#adminApiUrlInput")?.value.trim();
  const remember = $("#rememberEmailCheckbox")?.checked;
  const errorBanner = $("#authErrorMessage");
  const loginBtn = $("#adminLoginBtn");

  if (!identifier || !password) {
    showAuthError("Please provide both email/username and password.");
    return;
  }

  if (apiUrl) {
    state.apiBase = apiUrl.replace(/\/+$/, "");
    localStorage.setItem(STATE_KEY_API, state.apiBase);
    const displayEl = $("#apiBaseDisplay");
    if (displayEl) displayEl.textContent = state.apiBase;
    updateEnvBadge();
  }

  if (remember) {
    localStorage.setItem(STATE_KEY_REMEMBER_EMAIL, identifier);
  } else {
    localStorage.removeItem(STATE_KEY_REMEMBER_EMAIL);
  }

  if (errorBanner) errorBanner.classList.add("hidden");
  if (loginBtn) {
    loginBtn.disabled = true;
    loginBtn.innerHTML = `<span>Authenticating...</span>`;
  }

  try {
    let token = "";
    let admin = null;

    // Primary: Dedicated Admin Auth API
    try {
      const res = await adminApi("/admin-auth/login", {
        method: "POST",
        body: JSON.stringify({ email_or_username: identifier, password }),
      });
      token = res?.data?.access_token;
      admin = res?.data?.admin;
    } catch (primaryErr) {
      // If endpoint doesn't exist on legacy backend, fallback to /auth/login with RBAC check
      if (primaryErr.status === 404) {
        const fallbackRes = await adminApi("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: identifier, password }),
        });
        token = fallbackRes?.data?.access_token;
        admin = fallbackRes?.data?.user;
      } else {
        throw primaryErr;
      }
    }

    if (!token) {
      throw new Error("Authentication response did not contain an admin access token.");
    }

    state.token = token;
    state.adminUser = admin;

    // Verify privilege against privileged endpoint
    await adminApi("/admin/overview");

    // Success: save token & transition to app
    localStorage.setItem(STATE_KEY_TOKEN, token);
    showAppView();
    updateAdminUserDisplay(admin);
    toast("Welcome to SmartResume.ai Admin Console!", "success");
    handleHashRouting();
  } catch (err) {
    state.token = "";
    state.adminUser = null;
    localStorage.removeItem(STATE_KEY_TOKEN);
    let msg = err.message || "Failed to authenticate administrator.";
    if (err.status === 403 || msg.toLowerCase().includes("forbidden") || msg.toLowerCase().includes("standard user")) {
      msg = "Access Denied: Standard user accounts cannot access the Admin Console. Administrator privileges are strictly required.";
    } else if (err.status === 401) {
      msg = "Invalid admin credentials or account locked. Please check your email and password.";
    }
    showAuthError(msg);
  } finally {
    if (loginBtn) {
      loginBtn.disabled = false;
      loginBtn.innerHTML = `<i data-lucide="log-in"></i><span>Authenticate Administrator</span>`;
      renderIcons();
    }
  }
}

async function handleAdminSignup(e) {
  e.preventDefault();
  const full_name = $("#adminSignupName")?.value.trim();
  const email = $("#adminSignupEmail")?.value.trim();
  const username = $("#adminSignupUsername")?.value.trim() || undefined;
  const invitation_token = $("#adminSignupToken")?.value.trim();
  const password = $("#adminSignupPassword")?.value;
  const confirm_password = $("#adminSignupConfirm")?.value;
  const errorBanner = $("#signupErrorMessage");
  const signupBtn = $("#adminSignupBtn");

  if (!full_name || !email || !invitation_token || !password || !confirm_password) {
    showSignupError("Please fill in all required fields.");
    return;
  }

  if (password.length < 8) {
    showSignupError("Password must be at least 8 characters long.");
    return;
  }

  if (password !== confirm_password) {
    showSignupError("Passwords do not match. Please re-enter.");
    return;
  }

  if (errorBanner) errorBanner.classList.add("hidden");
  if (signupBtn) {
    signupBtn.disabled = true;
    signupBtn.innerHTML = `<span>Provisioning Admin Account...</span>`;
  }

  try {
    const res = await adminApi("/admin-auth/signup", {
      method: "POST",
      body: JSON.stringify({
        email,
        full_name,
        username,
        invitation_token,
        password,
        confirm_password,
      }),
    });

    const token = res?.data?.access_token;
    const admin = res?.data?.admin;

    if (!token) {
      throw new Error("Admin registration did not return a session token.");
    }

    state.token = token;
    state.adminUser = admin;
    localStorage.setItem(STATE_KEY_TOKEN, token);

    showAppView();
    updateAdminUserDisplay(admin);
    toast("Administrator account provisioned successfully!", "success");
    handleHashRouting();
  } catch (err) {
    let msg = err.message || "Failed to create administrator account.";
    if (err.status === 400 && msg.toLowerCase().includes("invitation")) {
      msg = "Invalid, expired, or already used invitation token. Please request a new invite from your Owner Administrator.";
    }
    showSignupError(msg);
  } finally {
    if (signupBtn) {
      signupBtn.disabled = false;
      signupBtn.innerHTML = `<i data-lucide="user-plus"></i><span>Create Administrator Account</span>`;
      renderIcons();
    }
  }
}

function showAuthError(msg) {
  const errorBanner = $("#authErrorMessage");
  if (errorBanner) {
    errorBanner.textContent = msg;
    errorBanner.classList.remove("hidden");
  }
}

function showSignupError(msg) {
  const errorBanner = $("#signupErrorMessage");
  if (errorBanner) {
    errorBanner.textContent = msg;
    errorBanner.classList.remove("hidden");
  }
}

function handleAdminLogout(msg = "") {
  state.token = "";
  state.adminUser = null;
  localStorage.removeItem(STATE_KEY_TOKEN);
  showAuthView();
  if (msg) toast(msg, "info");
}

async function verifyAdminSession() {
  try {
    // 1. Fetch current admin profile
    let adminProfile = null;
    try {
      const meRes = await adminApi("/admin-auth/me");
      adminProfile = meRes?.data;
    } catch (_) {
      // Fallback if legacy token
    }

    state.adminUser = adminProfile;
    updateAdminUserDisplay(adminProfile);

    // 2. Fetch overview to ensure active privileges
    await adminApi("/admin/overview");

    showAppView();
    handleHashRouting();
  } catch (_) {
    showAuthView();
  }
}

function updateAdminUserDisplay(admin) {
  if (!admin) return;
  const nameEl = $("#adminUserFullName");
  const emailEl = $("#adminUserEmail");
  const avatarEl = $("#adminAvatarInitials");
  const badgeEl = $("#adminUserRoleBadge");
  const sessionRole = $("#sessionRoleBadge");

  const name = admin.full_name || admin.username || "Administrator";
  const email = admin.email || "";
  const role = admin.role || "ADMIN";

  if (nameEl) nameEl.textContent = name;
  if (emailEl) emailEl.textContent = email;
  if (avatarEl) {
    const initials = name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2) || "AD";
    avatarEl.textContent = initials;
  }
  if (badgeEl) {
    badgeEl.textContent = role;
    badgeEl.className = `badge ${role === 'OWNER_ADMIN' ? 'badge-owner' : (role === 'STAFF_ADMIN' ? 'badge-staff' : 'badge-readonly')}`;
  }
  if (sessionRole) {
    sessionRole.textContent = role;
    sessionRole.className = `badge ${role === 'OWNER_ADMIN' ? 'badge-owner' : (role === 'STAFF_ADMIN' ? 'badge-staff' : 'badge-readonly')}`;
  }
}

function showAuthView() {
  $("#adminAuthView")?.classList.remove("hidden");
  $("#adminAppView")?.classList.add("hidden");
  renderIcons();
}

function showAppView() {
  $("#adminAuthView")?.classList.add("hidden");
  $("#adminAppView")?.classList.remove("hidden");
  renderIcons();
}

// Navigation & Routing
const ROUTE_MAP = {
  "#/dashboard": "overview",
  "#/overview": "overview",
  "#/users": "users",
  "#/admin-team": "admin-team",
  "#/ai-ops": "ai-ops",
  "#/feature-flags": "feature-flags",
  "#/audit-logs": "audit-logs",
};

function handleHashRouting() {
  const hash = (window.location.hash || "#/overview").split("?")[0];
  const targetTab = ROUTE_MAP[hash] || "overview";
  activateTab(targetTab, false);
}

const TAB_TITLES = {
  "overview": "Overview & Health",
  "users": "User Directory & RBAC",
  "admin-team": "Admin Team & Invites",
  "ai-ops": "AI Ops & Telemetry",
  "feature-flags": "Feature Flags",
  "audit-logs": "Security Audit Trail",
};

function activateTab(tabName, updateHash = true) {
  state.activeTab = tabName;

  // Highlight Nav Buttons
  $$(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  // Switch Tab Panels
  $$(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  const panelMap = {
    "overview": "panelOverview",
    "users": "panelUsers",
    "admin-team": "panelAdminTeam",
    "ai-ops": "panelAiOps",
    "feature-flags": "panelFeatureFlags",
    "audit-logs": "panelAuditLogs",
  };
  const targetPanel = $(`#${panelMap[tabName]}`);
  if (targetPanel) targetPanel.classList.add("active");

  // Update Title
  const titleEl = $("#viewTitle");
  if (titleEl) titleEl.textContent = TAB_TITLES[tabName] || "Admin Console";

  // Update URL Hash
  if (updateHash) {
    window.history.pushState(null, "", `#/${tabName}`);
  }

  // Load active tab data
  refreshActiveView();
  renderIcons();
}

function refreshActiveView() {
  if (state.activeTab === "overview") loadOverview();
  else if (state.activeTab === "users") loadUsers(state.currentPage, state.userSearchQuery);
  else if (state.activeTab === "admin-team") loadAdminTeam();
  else if (state.activeTab === "ai-ops") loadAiOps();
  else if (state.activeTab === "feature-flags") loadFeatureFlags();
  else if (state.activeTab === "audit-logs") loadAuditLogs();
}

// TAB 1: OVERVIEW LOADER
async function loadOverview() {
  try {
    const res = await adminApi("/admin/overview");
    const data = res?.data || {};

    if ($("#kpiTotalUsers")) $("#kpiTotalUsers").textContent = data.user_metrics?.total_users ?? 0;
    if ($("#kpiActiveUsers")) $("#kpiActiveUsers").textContent = `${data.user_metrics?.active_users ?? 0} active users`;
    if ($("#kpiTotalResumes")) $("#kpiTotalResumes").textContent = data.document_metrics?.total_resumes ?? 0;
    if ($("#kpiTotalVersions")) $("#kpiTotalVersions").textContent = `${data.document_metrics?.total_versions ?? 0} versions recorded`;
    if ($("#kpiTotalInterviews")) $("#kpiTotalInterviews").textContent = data.interview_metrics?.total_sessions ?? 0;
    if ($("#kpiCompletedInterviews")) $("#kpiCompletedInterviews").textContent = `${data.interview_metrics?.completed_sessions ?? 0} completed sessions`;

    const aiOps = data.ai_ops_summary || {};
    if ($("#kpiAiOpsStatus")) $("#kpiAiOpsStatus").textContent = aiOps.healthy ? "Operational" : "Degraded";
    if ($("#kpiAiOpsLatency")) $("#kpiAiOpsLatency").textContent = `Avg Latency: ${aiOps.avg_latency_ms || 185} ms`;

    // Render Quick Flags
    const flags = data.feature_flags || {};
    const flagsContainer = $("#quickFlagsList");
    if (flagsContainer) {
      flagsContainer.innerHTML = Object.entries(flags).slice(0, 4).map(([k, v]) => `
        <div class="health-item">
          <span>${formatFlagName(k)}</span>
          <label class="toggle-switch">
            <input type="checkbox" ${v ? "checked" : ""} onchange="toggleAdminFeatureFlag('${k}', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
      `).join("");
    }
  } catch (err) {
    toast(`Failed to load overview: ${err.message}`, "error");
  }
}

// TAB 2: USERS DIRECTORY LOADER
async function loadUsers(page = 1, search = "") {
  state.currentPage = page;
  const tbody = $("#usersTableBody");
  if (!tbody) return;

  try {
    const res = await adminApi(`/admin/users?page=${page}&page_size=20&search=${encodeURIComponent(search)}`);
    const data = res?.data || {};
    const users = data.users || [];
    const total = data.total || 0;

    $("#userCountSummary").textContent = `Showing ${users.length} of ${total} registered user accounts`;

    if (users.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center p-4 text-muted">No users found matching query.</td></tr>`;
      return;
    }

    tbody.innerHTML = users.map((u) => {
      const isAdmin = (u.role || "").toUpperCase() === "ADMIN";
      const isSelf = state.adminUser && state.adminUser.email === u.email;
      const createdDate = u.created_at ? new Date(u.created_at).toLocaleDateString() : "--";
      return `
        <tr>
          <td>
            <strong>${escapeHtml(u.full_name || 'User')}</strong>
            <span class="text-xs text-muted block">${escapeHtml(u.email)}</span>
          </td>
          <td>
            <span class="badge ${isAdmin ? 'badge-admin' : 'badge-user'}">${escapeHtml(u.role)}</span>
          </td>
          <td><strong>${u.resume_count || 0}</strong></td>
          <td>
            <span class="badge ${u.is_verified ? 'badge-success' : 'badge-warning'}">
              ${u.is_verified ? 'VERIFIED' : 'PENDING'}
            </span>
          </td>
          <td class="text-xs text-muted">${createdDate}</td>
          <td class="text-right">
            ${isSelf ? '<span class="text-xs text-muted">Current Session</span>' : `
              <button class="btn btn-xs ${isAdmin ? 'btn-danger-outline' : 'btn-success-outline'}" onclick="updateAdminUserRole(${u.id}, '${isAdmin ? 'USER' : 'ADMIN'}')">
                <i data-lucide="${isAdmin ? 'shield-minus' : 'shield-check'}"></i>
                <span>${isAdmin ? 'Demote to User' : 'Make Admin'}</span>
              </button>
            `}
          </td>
        </tr>
      `;
    }).join("");

    renderPagination(data.page, data.total_pages);
    renderIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center p-4">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderPagination(current, totalPages) {
  const container = $("#userPaginationControls");
  if (!container || totalPages <= 1) {
    if (container) container.innerHTML = "";
    return;
  }
  container.innerHTML = `
    <button class="btn btn-secondary btn-xs" ${current <= 1 ? "disabled" : ""} onclick="loadUsers(${current - 1}, state.userSearchQuery)">Previous</button>
    <span class="text-xs text-muted" style="padding: 0 0.5rem;">Page ${current} of ${totalPages}</span>
    <button class="btn btn-secondary btn-xs" ${current >= totalPages ? "disabled" : ""} onclick="loadUsers(${current + 1}, state.userSearchQuery)">Next</button>
  `;
}

window.updateAdminUserRole = async function(userId, newRole) {
  if (!confirm(`Are you sure you want to change this user's role to ${newRole}?`)) return;

  try {
    const res = await adminApi(`/admin/users/${userId}/role`, {
      method: "POST",
      body: JSON.stringify({ role: newRole }),
    });
    toast(res?.message || `User role updated to ${newRole}.`, "success");
    loadUsers(state.currentPage, state.userSearchQuery);
  } catch (err) {
    toast(`Failed to update role: ${err.message}`, "error");
  }
};

// TAB 3: ADMIN TEAM & INVITATIONS
async function loadAdminTeam() {
  await loadAdminInvitations();
}

window.loadAdminInvitations = async function() {
  const tbody = $("#invitationsTableBody");
  if (!tbody) return;

  try {
    const res = await adminApi("/admin-auth/invitations");
    const invites = res?.data || [];

    if (!Array.isArray(invites) || invites.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center p-4 text-muted">No invitations issued yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = invites.map((inv) => {
      const createdStr = inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "--";
      const expiresStr = inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : "--";
      const isExpired = new Date(inv.expires_at) < new Date();
      let statusBadge = `<span class="badge badge-success">ACTIVE</span>`;
      if (inv.is_consumed) {
        statusBadge = `<span class="badge badge-user">CONSUMED</span>`;
      } else if (isExpired) {
        statusBadge = `<span class="badge badge-danger">EXPIRED</span>`;
      }

      return `
        <tr>
          <td><strong>${escapeHtml(inv.email)}</strong></td>
          <td><span class="badge ${inv.role === 'OWNER_ADMIN' ? 'badge-owner' : 'badge-staff'}">${escapeHtml(inv.role)}</span></td>
          <td class="text-xs text-muted">${createdStr}</td>
          <td class="text-xs text-muted">${expiresStr}</td>
          <td>${statusBadge}</td>
          <td class="text-right">
            ${(!inv.is_consumed && !isExpired) ? `
              <button class="btn btn-danger-outline btn-xs" onclick="revokeAdminInvitation(${inv.id})">
                <i data-lucide="x-circle"></i> Revoke
              </button>
            ` : '<span class="text-xs text-muted">—</span>'}
          </td>
        </tr>
      `;
    }).join("");

    renderIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center p-4 text-muted">${escapeHtml(err.message)}</td></tr>`;
  }
};

async function handleCreateInvitation(e) {
  e.preventDefault();
  const email = $("#inviteEmailInput")?.value.trim();
  const role = $("#inviteRoleSelect")?.value || "STAFF_ADMIN";
  const hours = parseInt($("#inviteExpiryInput")?.value || "48", 10);
  const btn = $("#createInviteBtn");

  if (!email) {
    toast("Please provide an administrator email address.", "error");
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>Creating Invitation...</span>`;
  }

  try {
    const res = await adminApi("/admin-auth/invitations", {
      method: "POST",
      body: JSON.stringify({
        email,
        role,
        expires_in_hours: hours,
      }),
    });

    const data = res?.data || {};
    state.latestInvite = data;

    const card = $("#latestInviteCard");
    const box = $("#latestInviteTokenBox");
    if (card && box) {
      box.textContent = data.raw_token || "Token Generated";
      card.classList.remove("hidden");
    }

    toast(`Invitation created for ${email}!`, "success");
    loadAdminInvitations();
    renderIcons();
  } catch (err) {
    toast(`Failed to create invitation: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="key"></i><span>Generate Invitation Token</span>`;
      renderIcons();
    }
  }
}

window.copyLatestInviteLink = function() {
  if (!state.latestInvite) return;
  const baseUrl = window.location.origin + window.location.pathname;
  const link = `${baseUrl}#/signup?token=${state.latestInvite.raw_token}&email=${encodeURIComponent(state.latestInvite.email)}`;
  navigator.clipboard.writeText(link).then(() => {
    toast("Invitation signup link copied to clipboard!", "success");
  }).catch(() => {
    prompt("Copy Invitation Signup Link:", link);
  });
};

window.copyLatestInviteToken = function() {
  if (!state.latestInvite?.raw_token) return;
  navigator.clipboard.writeText(state.latestInvite.raw_token).then(() => {
    toast("Raw invitation token copied to clipboard!", "success");
  }).catch(() => {
    prompt("Copy Invitation Token:", state.latestInvite.raw_token);
  });
};

window.revokeAdminInvitation = async function(invId) {
  if (!confirm("Are you sure you want to revoke this invitation token?")) return;
  try {
    await adminApi(`/admin-auth/invitations/${invId}`, { method: "DELETE" });
    toast("Invitation revoked successfully.", "success");
    loadAdminInvitations();
  } catch (err) {
    toast(`Failed to revoke invitation: ${err.message}`, "error");
  }
};

// TAB 4: AI OPS LOADER
async function loadAiOps() {
  try {
    const res = await adminApi("/admin/ai-ops");
    const data = res?.data || {};

    if ($("#aiPrimaryModel")) $("#aiPrimaryModel").textContent = data.primary_model || "gemini-2.5-flash";
    if ($("#aiFallbackEngine")) $("#aiFallbackEngine").textContent = data.fallback_engine || "deterministic-v2";
    if ($("#aiTotalRequests")) $("#aiTotalRequests").textContent = data.total_requests_24h ?? "--";
    if ($("#aiFallbackRate")) $("#aiFallbackRate").textContent = `Fallback Rate: ${data.fallback_rate_pct ?? 0}%`;

    const lat = data.latency_percentiles_ms || {};
    if ($("#aiLatencyMetric")) $("#aiLatencyMetric").textContent = `${lat.p50 ?? "--"} ms / ${lat.p99 ?? "--"} ms`;

    // Feature breakdown
    const breakdown = data.breakdown_by_feature || {};
    const tbody = $("#aiFeatureBreakdownBody");
    if (tbody) {
      tbody.innerHTML = Object.entries(breakdown).map(([k, v]) => `
        <tr>
          <td><strong>${formatFlagName(k)}</strong></td>
          <td>${v.calls ?? 0} calls</td>
          <td><span class="badge ${parseFloat(v.fallback_rate) > 5 ? 'badge-warning' : 'badge-success'}">${v.fallback_rate || "0.0%"}</span></td>
          <td><span class="badge badge-success">HEALTHY</span></td>
        </tr>
      `).join("");
    }
  } catch (err) {
    toast(`Failed to load AI telemetry: ${err.message}`, "error");
  }
}

// TAB 5: FEATURE FLAGS LOADER
async function loadFeatureFlags() {
  const container = $("#fullFlagsContainer");
  if (!container) return;

  try {
    const res = await adminApi("/admin/feature-flags");
    const flags = res?.data || {};

    const FLAG_DESCRIPTIONS = {
      "voice_interview_enabled": "Speech-to-text audio capture, live transcription, and speaking rate analysis in Mock Interview sessions.",
      "focus_coaching_enabled": "Client-side Attention HUD evaluating gaze stability and eye-contact indicators.",
      "smartbuild_ai_wizard": "7-step conversational AI wizard for creating grounded resumes from scratch.",
      "gemini_live_mode": "Real-time AI evaluation and continuous streaming generation with Google GenAI.",
      "job_radar_crawler": "Automated career opportunity scanning and job match ranking service.",
      "international_workspace": "Multi-country localization rules, ATS compliance checks, and regional formatting.",
    };

    container.innerHTML = Object.entries(flags).map(([k, v]) => `
      <div class="flag-card">
        <div class="flag-info">
          <strong>${formatFlagName(k)}</strong>
          <span>${FLAG_DESCRIPTIONS[k] || "System operational feature flag toggle."}</span>
          <code class="text-xs text-muted block" style="margin-top: 0.25rem;">${k}</code>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" ${v ? "checked" : ""} onchange="toggleAdminFeatureFlag('${k}', this.checked)">
          <span class="toggle-slider"></span>
        </label>
      </div>
    `).join("");
  } catch (err) {
    toast(`Failed to load feature flags: ${err.message}`, "error");
  }
}

window.toggleAdminFeatureFlag = async function(flagName, enabled) {
  try {
    await adminApi("/admin/feature-flags", {
      method: "PUT",
      body: JSON.stringify({ flags: { [flagName]: enabled } }),
    });
    toast(`Feature flag '${flagName}' is now ${enabled ? 'ENABLED' : 'DISABLED'}.`, "success");
  } catch (err) {
    toast(`Failed to update flag: ${err.message}`, "error");
    loadFeatureFlags();
  }
};

// TAB 6: AUDIT LOGS LOADER
async function loadAuditLogs() {
  const tbody = $("#auditLogsTableBody");
  if (!tbody) return;

  try {
    const res = await adminApi("/admin/audit-logs?limit=50");
    const logs = res?.data || [];

    if (!Array.isArray(logs) || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-muted">No security audit events recorded.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map((l) => {
      const timeStr = l.timestamp ? new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "--";
      const sevBadge = l.severity === "WARNING" ? "badge-warning" : (l.severity === "CRITICAL" ? "badge-danger" : "badge-success");
      return `
        <tr>
          <td class="text-xs text-muted" style="white-space: nowrap;">${timeStr}</td>
          <td><strong>${escapeHtml(l.actor)}</strong></td>
          <td><code>${escapeHtml(l.action)}</code></td>
          <td class="text-xs">${escapeHtml(l.details)}</td>
          <td><span class="badge ${sevBadge}">${escapeHtml(l.severity || 'INFO')}</span></td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center p-4">${escapeHtml(err.message)}</td></tr>`;
  }
}

function formatFlagName(rawKey) {
  return rawKey
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
