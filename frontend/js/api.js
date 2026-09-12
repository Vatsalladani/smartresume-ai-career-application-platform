const API = (() => {
  const isDevHost = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";
  const defaultBaseUrl = (isDevHost && window.location.port !== "8000")
    ? "http://127.0.0.1:8000/api/v1"
    : `${window.location.origin}/api/v1`;
  const baseUrl = localStorage.getItem("apiBaseUrl") || defaultBaseUrl;

  function getAccessToken() {
    return localStorage.getItem("accessToken");
  }

  function getRefreshToken() {
    return localStorage.getItem("refreshToken");
  }

  function setSession(data) {
    localStorage.setItem("accessToken", data.access_token);
    localStorage.setItem("refreshToken", data.refresh_token);
    localStorage.setItem("user", JSON.stringify(data.user));
  }

  function clearSession() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("user");
  }

  async function refreshSession() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    const response = await fetch(`${baseUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearSession();
      return false;
    }
    const payload = await response.json();
    setSession(payload.data);
    return true;
  }

  async function request(path, options = {}, retry = true) {
    const headers = options.headers ? { ...options.headers } : {};
    const body = options.body;
    const isForm = body instanceof FormData;
    if (!isForm && body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    if (options.auth !== false && getAccessToken()) {
      headers.Authorization = `Bearer ${getAccessToken()}`;
    }

    const response = await fetch(`${baseUrl}${path}`, {
      method: options.method || "GET",
      headers,
      body: isForm || typeof body === "string" ? body : body ? JSON.stringify(body) : undefined,
    });

    if (response.status === 401 && retry && options.auth !== false) {
      const refreshed = await refreshSession();
      if (refreshed) return request(path, options, false);
    }

    if (options.responseType === "blob") {
      if (!response.ok) throw new Error("Download failed.");
      return response.blob();
    }

    const payload = await response.json().catch(() => ({ success: false, message: "Invalid server response." }));
    if (!response.ok || payload.success === false) {
      throw new Error(payload.message || "Request failed.");
    }
    return payload.data;
  }

  return {
    baseUrl,
    request,
    setSession,
    clearSession,
    getAccessToken,
    getRefreshToken,
  };
})();
