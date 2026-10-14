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
  resumePage: 1,
  resumeSearchQuery: "",
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
  const apiInput = $("#adminApiUrlInput");
  if (apiInput) apiInput.value = state.apiBase;

  const displayEl = $("#apiBaseDisplay");
  if (displayEl) displayEl.textContent = state.apiBase;

  const remembered = localStorage.getItem(STATE_KEY_REMEMBER_EMAIL);
  if (remembered && $("#adminEmailInput")) {
    $("#adminEmailInput").value = remembered;
    if ($("#rememberEmailCheckbox")) $("#rememberEmailCheckbox").checked = true;
  }

  updateEnvBadge();

  // Bind Form Submissions
  $("#adminLoginForm")?.addEventListener("submit", handleAdminLogin);
  $("#adminSignupForm")?.addEventListener("submit", handleAdminSignup);
  $("#createInviteForm")?.addEventListener("submit", handleCreateInvitation);
  $("#aiControlsForm")?.addEventListener("submit", handleSaveAiControls);
  $("#announcementForm")?.addEventListener("submit", handleSaveAnnouncement);
  $("#interviewConfigForm")?.addEventListener("submit", handleSaveInterviewConfig);
  $("#quotasConfigForm")?.addEventListener("submit", handleSaveQuotas);

  // Bind Controls
  $("#adminLogoutBtn")?.addEventListener("click", () => handleAdminLogout("Signed out successfully."));
  $("#refreshCurrentViewBtn")?.addEventListener("click", () => refreshActiveView());
  $("#refreshAuditLogsBtn")?.addEventListener("click", () => loadAuditLogs());
  $("#switchApiTargetBtn")?.addEventListener("click", promptChangeApiTarget);

  // Nav Clicks
  $$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      if (tab) activateTab(tab);
    });
  });

  // User Search
  let searchTimeout = null;
  $("#userSearchInput")?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.userSearchQuery = e.target.value.trim();
      loadUsers(1, state.userSearchQuery);
    }, 300);
  });

  // Resume Search
  let resumeSearchTimeout = null;
  $("#resumeSearchInput")?.addEventListener("input", (e) => {
    clearTimeout(resumeSearchTimeout);
    resumeSearchTimeout = setTimeout(() => {
      state.resumeSearchQuery = e.target.value.trim();
      loadResumes(1, state.resumeSearchQuery);
    }, 300);
  });

  // Hash change routing
  window.addEventListener("hashchange", handleHashRouting);

  // Parse invite tokens in URL if on signup page
  checkUrlForInviteToken();

  // If token exists, verify session; otherwise show login
  if (state.token) {
    verifyAdminSession();
  } else {
    showAuthView();
  }
}

function updateEnvBadge() {
  const badge = $("#activeEnvBadge");
  if (!badge) return;
  const isLocal = state.apiBase.includes("localhost") || state.apiBase.includes("127.0.0.1");
  badge.textContent = isLocal ? "LOCAL DEV" : "PRODUCTION";
  badge.className = `badge-env ${isLocal ? "env-local" : "env-prod"}`;
}

window.setApiTarget = function(url) {
  const input = $("#adminApiUrlInput");
  if (input) input.value = url;
};

function promptChangeApiTarget() {
  const newTarget = prompt("Enter backend API base URL:", state.apiBase);
  if (newTarget && newTarget.trim()) {
    state.apiBase = newTarget.trim().replace(/\/+$/, "");
    localStorage.setItem(STATE_KEY_API, state.apiBase);
    const displayEl = $("#apiBaseDisplay");
    if (displayEl) displayEl.textContent = state.apiBase;
    updateEnvBadge();
    toast(`Target API changed to: ${state.apiBase}`, "info");
    refreshActiveView();
  }
}

window.switchAuthMode = function(mode) {
  const loginForm = $("#adminLoginForm");
  const signupForm = $("#adminSignupForm");
  const tabLogin = $("#tabLoginBtn");
  const tabSignup = $("#tabSignupBtn");

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

  const params = new URLSearchParams(window.location.search);
  if (params.get("token")) {
    token = params.get("token");
    email = params.get("email") || "";
  }

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

    try {
      const res = await adminApi("/admin-auth/login", {
        method: "POST",
        body: JSON.stringify({ email_or_username: identifier, password }),
      });
      token = res?.data?.access_token;
      admin = res?.data?.admin;
    } catch (adminErr) {
      if (adminErr.status === 404 || adminErr.status === 401) {
        // Fallback check: legacy user auth if promoting initial admin
        const fbRes = await adminApi("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: identifier, password }),
        });
        if (fbRes?.data?.user?.role === "USER") {
          const err = new Error("Access Denied: Standard user accounts cannot access the dedicated Admin Portal.");
          err.status = 403;
          throw err;
        }
        token = fbRes?.data?.access_token;
        admin = {
          email: fbRes?.data?.user?.email,
          full_name: fbRes?.data?.user?.full_name,
          role: fbRes?.data?.user?.role,
        };
      } else {
        throw adminErr;
      }
    }

    if (!token) throw new Error("Authentication failed to provide a valid token.");

    state.token = token;
    state.adminUser = admin;
    localStorage.setItem(STATE_KEY_TOKEN, token);

    showAppView();
    updateAdminUserDisplay(admin);
    toast(`Welcome, ${admin?.full_name || 'Administrator'}!`, "success");
    handleHashRouting();
  } catch (err) {
    let msg = err.message || "Failed to authenticate administrator.";
    if (err.status === 403) {
      msg = "Access Denied: Standard user accounts cannot access the dedicated Admin Portal.";
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

    if (!token) throw new Error("Admin registration did not return a session token.");

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
    let adminProfile = null;
    try {
      const meRes = await adminApi("/admin-auth/me");
      adminProfile = meRes?.data;
    } catch (_) {}

    state.adminUser = adminProfile;
    updateAdminUserDisplay(adminProfile);

    // Verify admin access
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
  "#/resumes": "resumes",
  "#/ai-ops": "ai-ops",
  "#/feature-flags": "feature-flags",
  "#/subscriptions": "subscriptions",
  "#/admin-team": "admin-team",
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
  "resumes": "Resumes & Templates",
  "ai-ops": "AI Ops & Gemini Controls",
  "feature-flags": "Feature Flags & Announcements",
  "subscriptions": "Subscriptions & Quotas",
  "admin-team": "Admin Team & Invites",
  "audit-logs": "Security Audit Trail",
};

function activateTab(tabName, updateHash = true) {
  state.activeTab = tabName;

  $$(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  $$(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  const panelMap = {
    "overview": "panelOverview",
    "users": "panelUsers",
    "resumes": "panelResumes",
    "ai-ops": "panelAiOps",
    "feature-flags": "panelFeatureFlags",
    "subscriptions": "panelSubscriptions",
    "admin-team": "panelAdminTeam",
    "audit-logs": "panelAuditLogs",
  };
  const targetPanel = $(`#${panelMap[tabName]}`);
  if (targetPanel) targetPanel.classList.add("active");

  const titleEl = $("#viewTitle");
  if (titleEl) titleEl.textContent = TAB_TITLES[tabName] || "Admin Console";

  if (updateHash) {
    window.history.pushState(null, "", `#/${tabName}`);
  }

  refreshActiveView();
  renderIcons();
}

function refreshActiveView() {
  if (state.activeTab === "overview") loadOverview();
  else if (state.activeTab === "users") loadUsers(state.currentPage, state.userSearchQuery);
  else if (state.activeTab === "resumes") loadResumes(state.resumePage, state.resumeSearchQuery);
  else if (state.activeTab === "ai-ops") loadAiOps();
  else if (state.activeTab === "feature-flags") loadFeatureFlags();
  else if (state.activeTab === "subscriptions") loadSubscriptions();
  else if (state.activeTab === "admin-team") loadAdminTeam();
  else if (state.activeTab === "audit-logs") loadAuditLogs();
}

// 1. OVERVIEW
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
    if ($("#kpiAiOpsLatency")) $("#kpiAiOpsLatency").textContent = `Avg Latency: ${aiOps.avg_latency_ms || 0} ms`;

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

// 2. USERS DIRECTORY
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
      tbody.innerHTML = `<tr><td colspan="7" class="text-center p-4 text-muted">No users found matching query.</td></tr>`;
      return;
    }

    tbody.innerHTML = users.map((u) => {
      const isAdmin = (u.role || "").toUpperCase() === "ADMIN";
      const isSelf = state.adminUser && state.adminUser.email === u.email;
      const createdDate = u.created_at ? new Date(u.created_at).toLocaleDateString() : "--";
      const planBadge = u.plan_name === 'EXECUTIVE' ? 'badge-exec' : (u.plan_name === 'PRO' ? 'badge-pro' : 'badge-free');
      const statusBadge = u.is_active ? '<span class="badge badge-active">ACTIVE</span>' : '<span class="badge badge-suspended">SUSPENDED</span>';

      return `
        <tr>
          <td>
            <strong>${escapeHtml(u.full_name || 'User')}</strong>
            <span class="text-xs text-muted block">${escapeHtml(u.email)}</span>
          </td>
          <td><span class="badge ${isAdmin ? 'badge-admin' : 'badge-user'}">${escapeHtml(u.role)}</span></td>
          <td><span class="badge ${planBadge}">${escapeHtml(u.plan_name || 'FREE')}</span></td>
          <td>${statusBadge}</td>
          <td><strong>${u.resume_count || 0}</strong></td>
          <td class="text-xs text-muted">${createdDate}</td>
          <td class="text-right">
            <button class="btn btn-secondary btn-xs" onclick="openUserModal(${u.id}, '${escapeHtml(u.email)}', '${u.plan_name}', ${u.is_active}, ${u.is_verified})">
              <i data-lucide="edit-3"></i> Edit
            </button>
            ${!isSelf ? `
              <button class="btn btn-xs ${isAdmin ? 'btn-danger-outline' : 'btn-success-outline'}" onclick="updateAdminUserRole(${u.id}, '${isAdmin ? 'USER' : 'ADMIN'}')">
                ${isAdmin ? 'Demote' : 'Make Admin'}
              </button>
            ` : ''}
          </td>
        </tr>
      `;
    }).join("");

    renderPagination(data.page, data.total_pages);
    renderIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center p-4">${escapeHtml(err.message)}</td></tr>`;
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

window.openUserModal = function(id, email, plan, isActive, isVerified) {
  $("#modalUserId").value = id;
  $("#modalUserEmail").value = email;
  $("#modalUserPlanSelect").value = plan || "FREE";
  $("#modalUserActiveToggle").checked = Boolean(isActive);
  $("#modalUserVerifiedToggle").checked = Boolean(isVerified);
  $("#userModalOverlay").classList.remove("hidden");
};

window.closeUserModal = function() {
  $("#userModalOverlay").classList.add("hidden");
};

window.saveUserModalChanges = async function() {
  const userId = $("#modalUserId").value;
  const newPlan = $("#modalUserPlanSelect").value;
  const isActive = $("#modalUserActiveToggle").checked;
  const isVerified = $("#modalUserVerifiedToggle").checked;

  try {
    await adminApi(`/admin/users/${userId}/status`, {
      method: "POST",
      body: JSON.stringify({ is_active: isActive, is_verified: isVerified }),
    });

    await adminApi(`/admin/users/${userId}/plan`, {
      method: "POST",
      body: JSON.stringify({ plan_name: newPlan }),
    });

    toast("User account updated successfully.", "success");
    closeUserModal();
    loadUsers(state.currentPage, state.userSearchQuery);
  } catch (err) {
    toast(`Failed to update user: ${err.message}`, "error");
  }
};

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

// 3. RESUMES & TEMPLATES
async function loadResumes(page = 1, search = "") {
  state.resumePage = page;
  const tbody = $("#resumesTableBody");
  if (!tbody) return;

  try {
    const res = await adminApi(`/admin/resumes?page=${page}&page_size=20&search=${encodeURIComponent(search)}`);
    const data = res?.data || {};
    const resumes = data.resumes || [];
    const total = data.total || 0;

    $("#resumeCountSummary").textContent = `Showing ${resumes.length} of ${total} resumes`;

    if (resumes.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center p-4 text-muted">No resumes found.</td></tr>`;
    } else {
      tbody.innerHTML = resumes.map((r) => {
        const updated = r.updated_at ? new Date(r.updated_at).toLocaleDateString() : "--";
        const scoreBadge = r.ats_score >= 80 ? 'badge-success' : (r.ats_score >= 60 ? 'badge-warning' : 'badge-danger');
        return `
          <tr>
            <td>
              <strong>${escapeHtml(r.title)}</strong>
              <span class="text-xs text-muted block">${escapeHtml(r.user_email)}</span>
            </td>
            <td>${escapeHtml(r.target_role || 'Unspecified')}</td>
            <td><span class="badge ${scoreBadge}">${r.ats_score} / 100</span></td>
            <td>${r.completeness_score}%</td>
            <td><strong>${r.version_count}</strong></td>
            <td class="text-xs text-muted">${updated}</td>
            <td class="text-right">
              <button class="btn btn-secondary btn-xs" onclick="inspectResume(${r.id})">
                <i data-lucide="eye"></i> Inspect
              </button>
            </td>
          </tr>
        `;
      }).join("");
    }

    renderResumePagination(data.page, data.total_pages);
    renderIcons();

    // Load templates status
    loadTemplatesStatus();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center p-4">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderResumePagination(current, totalPages) {
  const container = $("#resumePaginationControls");
  if (!container || totalPages <= 1) {
    if (container) container.innerHTML = "";
    return;
  }
  container.innerHTML = `
    <button class="btn btn-secondary btn-xs" ${current <= 1 ? "disabled" : ""} onclick="loadResumes(${current - 1}, state.resumeSearchQuery)">Previous</button>
    <span class="text-xs text-muted" style="padding: 0 0.5rem;">Page ${current} of ${totalPages}</span>
    <button class="btn btn-secondary btn-xs" ${current >= totalPages ? "disabled" : ""} onclick="loadResumes(${current + 1}, state.resumeSearchQuery)">Next</button>
  `;
}

window.inspectResume = async function(resumeId) {
  try {
    const res = await adminApi(`/admin/resumes/${resumeId}`);
    const r = res?.data || {};

    $("#resumeModalTitle").textContent = `Inspect Resume: ${r.title}`;
    const body = $("#resumeModalBody");
    const parsed = r.parsed_content || {};

    body.innerHTML = `
      <div style="margin-bottom: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
        <div><strong>User:</strong> ${escapeHtml(r.user_email || 'unknown')}</div>
        <div><strong>Target Role:</strong> ${escapeHtml(r.target_role || 'N/A')}</div>
        <div><strong>ATS Score:</strong> <span class="badge badge-success">${r.ats_score}/100</span></div>
      </div>
      <div class="card" style="margin-bottom: 1rem; background: var(--bg-surface); padding: 1rem;">
        <h4>Professional Summary</h4>
        <p class="text-xs" style="margin-top: 0.25rem;">${escapeHtml(parsed.summary || 'No summary recorded.')}</p>
      </div>
      <div class="card" style="margin-bottom: 1rem; background: var(--bg-surface); padding: 1rem;">
        <h4>Skills & Experience Snapshot</h4>
        <p class="text-xs text-muted">${parsed.skills ? Object.values(parsed.skills).flat().join(', ') : 'No skills categorized.'}</p>
      </div>
      <div>
        <h4>Version History (${r.versions?.length || 0})</h4>
        <ul style="padding-left: 1.25rem; margin-top: 0.5rem; font-size: 0.8125rem;">
          ${(r.versions || []).map(v => `<li>Version ${v.version_number}: ${escapeHtml(v.changelog)} (${v.created_at ? new Date(v.created_at).toLocaleString() : ''})</li>`).join('')}
        </ul>
      </div>
    `;

    $("#resumeModalOverlay").classList.remove("hidden");
  } catch (err) {
    toast(`Failed to inspect resume: ${err.message}`, "error");
  }
};

window.closeResumeModal = function() {
  $("#resumeModalOverlay").classList.add("hidden");
};

async function loadTemplatesStatus() {
  const grid = $("#templatesGrid");
  if (!grid) return;

  try {
    const res = await adminApi("/admin/templates");
    const list = res?.data?.templates || [];

    grid.innerHTML = list.map((t) => `
      <div class="template-card">
        <div>
          <div class="template-header">
            <strong>${escapeHtml(t.name)}</strong>
            <span class="badge ${t.enabled ? 'badge-success' : 'badge-danger'}">${t.enabled ? 'ACTIVE' : 'DISABLED'}</span>
          </div>
          <p class="text-xs text-muted">${escapeHtml(t.description)}</p>
          <code class="text-xs block" style="margin-top: 0.5rem;">${t.id}</code>
        </div>
        <div style="margin-top: 1rem; display: flex; justify-content: flex-end;">
          <label class="toggle-switch">
            <input type="checkbox" ${t.enabled ? "checked" : ""} onchange="toggleTemplateStatus('${t.id}', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>
    `).join("");
  } catch (err) {
    grid.innerHTML = `<p class="text-danger">Failed to load templates: ${err.message}</p>`;
  }
}

window.toggleTemplateStatus = async function(templateId, enabled) {
  try {
    await adminApi(`/admin/templates/${templateId}/status`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    });
    toast(`Template ${templateId} is now ${enabled ? 'ENABLED' : 'DISABLED'}.`, "success");
    loadTemplatesStatus();
  } catch (err) {
    toast(`Failed to update template: ${err.message}`, "error");
    loadTemplatesStatus();
  }
};

// 4. AI OPS & GEMINI CONTROLS
async function loadAiOps() {
  try {
    const res = await adminApi("/admin/ai-ops");
    const data = res?.data || {};

    if ($("#aiPrimaryModel")) $("#aiPrimaryModel").textContent = data.primary_model || "gemini-2.5-flash";
    if ($("#aiFallbackEngine")) $("#aiFallbackEngine").textContent = "deterministic-rule-v2";
    if ($("#aiTotalRequests")) $("#aiTotalRequests").textContent = data.total_requests_24h ?? 0;
    if ($("#aiFallbackRate")) $("#aiFallbackRate").textContent = `Fallback Rate: ${data.fallback_rate_pct ?? 0}%`;

    const lat = data.latency_percentiles_ms || {};
    if ($("#aiLatencyMetric")) $("#aiLatencyMetric").textContent = `${lat.p50 ?? 0} ms / ${lat.p99 ?? 0} ms`;

    // Populate AI Controls Form
    const configRes = await adminApi("/admin/ai-config");
    const cfg = configRes?.data || {};

    if ($("#aiPrimaryModelSelect")) $("#aiPrimaryModelSelect").value = cfg.gemini_primary_model || "gemini-2.5-flash";
    if ($("#aiForceFallbackToggle")) $("#aiForceFallbackToggle").checked = Boolean(cfg.gemini_force_deterministic_fallback);
    if ($("#aiTemperatureInput")) $("#aiTemperatureInput").value = cfg.gemini_temperature ?? 0.2;
    if ($("#aiTimeoutInput")) $("#aiTimeoutInput").value = cfg.gemini_timeout_seconds ?? 15;

    // Feature breakdown
    const breakdown = data.breakdown_by_feature || {};
    const tbody = $("#aiFeatureBreakdownBody");
    if (tbody) {
      const keys = Object.keys(breakdown);
      if (keys.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center p-4 text-muted">No AI calls recorded yet in the last 24h.</td></tr>`;
      } else {
        tbody.innerHTML = Object.entries(breakdown).map(([k, v]) => `
          <tr>
            <td><strong>${formatFlagName(k)}</strong></td>
            <td>${v.calls ?? 0} calls</td>
            <td><span class="badge ${parseFloat(v.fallback_rate) > 5 ? 'badge-warning' : 'badge-success'}">${v.fallback_rate || "0.0%"}</span></td>
            <td><span class="badge badge-success">HEALTHY</span></td>
          </tr>
        `).join("");
      }
    }
  } catch (err) {
    toast(`Failed to load AI telemetry: ${err.message}`, "error");
  }
}

async function handleSaveAiControls(e) {
  e.preventDefault();
  const primaryModel = $("#aiPrimaryModelSelect")?.value;
  const forceFallback = $("#aiForceFallbackToggle")?.checked;
  const temperature = parseFloat($("#aiTemperatureInput")?.value || "0.2");
  const timeout = parseInt($("#aiTimeoutInput")?.value || "15", 10);

  try {
    await adminApi("/admin/ai-config", {
      method: "PUT",
      body: JSON.stringify({
        gemini_primary_model: primaryModel,
        gemini_force_deterministic_fallback: forceFallback,
        gemini_temperature: temperature,
        gemini_timeout_seconds: timeout,
      }),
    });
    toast("AI Configuration updated successfully with immediate live propagation!", "success");
    loadAiOps();
  } catch (err) {
    toast(`Failed to save AI config: ${err.message}`, "error");
  }
}

// 5. FEATURE FLAGS & ANNOUNCEMENTS
async function loadFeatureFlags() {
  const container = $("#fullFlagsContainer");
  if (!container) return;

  try {
    const res = await adminApi("/admin/feature-flags");
    const flags = res?.data || {};

    const FLAG_DESCRIPTIONS = {
      "text_interview_enabled": "Enable interactive multi-turn text mock interview practice with STAR scoring.",
      "voice_interview_enabled": "Speech-to-text audio capture, live voice prompts, and rate analysis in Interview Practice.",
      "focus_coaching_enabled": "Real-time Attention HUD tracking gaze stability and eye contact during interview practice.",
      "strict_focus_mode_enabled": "Allow candidates to opt-in to Strict Focus Practice with automated violation termination.",
      "smartbuild_ai_wizard": "7-step conversational AI wizard for building grounded resumes from scratch.",
      "gemini_live_mode": "Live AI generation and evaluation with Google Gemini API.",
      "job_radar_crawler": "Automated career opportunity scanning and job match tracking service.",
      "international_workspace": "Multi-region compliance checks and international resume format adaptations.",
      "public_signup_enabled": "Permit new candidate account registration on the public application.",
      "maintenance_mode": "Put the public platform into read-only maintenance mode with advisory banner.",
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

    // Load Announcement
    const annRes = await adminApi("/admin/announcement");
    const ann = annRes?.data || {};
    if ($("#announcementEnabledToggle")) $("#announcementEnabledToggle").checked = Boolean(ann.enabled);
    if ($("#announcementTextInput")) $("#announcementTextInput").value = ann.text || "";

    // Load Interview Simulator Configuration
    const intRes = await adminApi("/admin/interview-config");
    const intCfg = intRes?.data || {};
    if ($("#adminInterviewDefaultDur") && intCfg.interview_default_duration !== undefined) {
      $("#adminInterviewDefaultDur").value = intCfg.interview_default_duration;
    }
    if ($("#adminInterviewMaxDur") && intCfg.interview_max_duration !== undefined) {
      $("#adminInterviewMaxDur").value = intCfg.interview_max_duration;
    }
    if ($("#adminStrictFocusMaxWarnings") && intCfg.strict_focus_max_warnings !== undefined) {
      $("#adminStrictFocusMaxWarnings").value = intCfg.strict_focus_max_warnings;
    }
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

async function handleSaveAnnouncement(e) {
  e.preventDefault();
  const enabled = $("#announcementEnabledToggle")?.checked;
  const text = $("#announcementTextInput")?.value.trim();

  try {
    await adminApi("/admin/announcement", {
      method: "PUT",
      body: JSON.stringify({ enabled, text }),
    });
    toast("Announcement banner updated successfully!", "success");
  } catch (err) {
    toast(`Failed to update announcement: ${err.message}`, "error");
  }
}

async function handleSaveInterviewConfig(e) {
  e.preventDefault();
  const defDur = parseInt($("#adminInterviewDefaultDur")?.value || "60", 10);
  const maxDur = parseInt($("#adminInterviewMaxDur")?.value || "120", 10);
  const maxWarnings = parseInt($("#adminStrictFocusMaxWarnings")?.value || "3", 10);

  try {
    await adminApi("/admin/interview-config", {
      method: "PUT",
      body: JSON.stringify({
        interview_default_duration: defDur,
        interview_max_duration: maxDur,
        strict_focus_max_warnings: maxWarnings,
      }),
    });
    toast("Interview engine configuration saved successfully!", "success");
  } catch (err) {
    toast(`Failed to update interview config: ${err.message}`, "error");
  }
}

// 6. SUBSCRIPTIONS & QUOTAS
async function loadSubscriptions() {
  const tbody = $("#subscriptionsTableBody");
  if (!tbody) return;

  try {
    const res = await adminApi("/admin/subscriptions?page=1&page_size=20");
    const subs = res?.data?.subscriptions || [];

    if (subs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center p-4 text-muted">No subscriptions recorded.</td></tr>`;
    } else {
      tbody.innerHTML = subs.map((s) => {
        const planBadge = s.plan_name === 'EXECUTIVE' ? 'badge-exec' : (s.plan_name === 'PRO' ? 'badge-pro' : 'badge-free');
        const updated = s.updated_at ? new Date(s.updated_at).toLocaleDateString() : "--";
        return `
          <tr>
            <td><strong>${escapeHtml(s.user_email)}</strong></td>
            <td><span class="badge ${planBadge}">${escapeHtml(s.plan_name)}</span></td>
            <td><span class="badge badge-active">${escapeHtml(s.status)}</span></td>
            <td class="text-xs text-muted">${updated}</td>
          </tr>
        `;
      }).join("");
    }

    // Load Quotas
    const qRes = await adminApi("/admin/quotas");
    const q = qRes?.data || {};

    if ($("#quotaFreeResumesInput")) $("#quotaFreeResumesInput").value = q.quota_free_resumes ?? 1;
    if ($("#quotaFreeTailorsInput")) $("#quotaFreeTailorsInput").value = q.quota_free_tailors ?? 3;
    if ($("#quotaFreeExportsInput")) $("#quotaFreeExportsInput").value = q.quota_free_exports ?? 5;
    if ($("#quotaProTailorsInput")) $("#quotaProTailorsInput").value = q.quota_pro_tailors ?? 50;
    if ($("#quotaProExportsInput")) $("#quotaProExportsInput").value = q.quota_pro_exports ?? 100;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center p-4">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function handleSaveQuotas(e) {
  e.preventDefault();
  const freeResumes = parseInt($("#quotaFreeResumesInput")?.value || "1", 10);
  const freeTailors = parseInt($("#quotaFreeTailorsInput")?.value || "3", 10);
  const freeExports = parseInt($("#quotaFreeExportsInput")?.value || "5", 10);
  const proTailors = parseInt($("#quotaProTailorsInput")?.value || "50", 10);
  const proExports = parseInt($("#quotaProExportsInput")?.value || "100", 10);

  try {
    await adminApi("/admin/quotas", {
      method: "PUT",
      body: JSON.stringify({
        quota_free_resumes: freeResumes,
        quota_free_tailors: freeTailors,
        quota_free_exports: freeExports,
        quota_pro_tailors: proTailors,
        quota_pro_exports: proExports,
      }),
    });
    toast("Default plan quotas updated successfully!", "success");
  } catch (err) {
    toast(`Failed to save quotas: ${err.message}`, "error");
  }
}

// 7. ADMIN TEAM & INVITATIONS
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
      body: JSON.stringify({ email, role, expires_in_hours: hours }),
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

// 8. SECURITY AUDIT TRAIL
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
