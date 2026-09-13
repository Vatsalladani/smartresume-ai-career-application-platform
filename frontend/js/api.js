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

    let response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: options.method || "GET",
        headers,
        body: isForm || typeof body === "string" ? body : body ? JSON.stringify(body) : undefined,
      });
    } catch (networkErr) {
      const err = new Error("Unable to connect to the server. Please ensure the backend is running and reachable.");
      err.isNetworkError = true;
      throw err;
    }

    if (response.status === 401 && retry && options.auth !== false) {
      const refreshed = await refreshSession();
      if (refreshed) return request(path, options, false);
    }

    if (options.responseType === "blob") {
      if (!response.ok) throw new Error("Download failed.");
      return response.blob();
    }

    const payload = await response.json().catch(() => null);
    if (!response.ok || (payload && payload.success === false)) {
      let errMsg = "";
      if (payload) {
        if (typeof payload.message === "string" && payload.message.trim()) {
          errMsg = payload.message;
        } else if (typeof payload.detail === "string" && payload.detail.trim()) {
          errMsg = payload.detail;
        } else if (Array.isArray(payload.detail) && payload.detail.length > 0) {
          errMsg = payload.detail.map((d) => d.msg || (typeof d === "string" ? d : JSON.stringify(d))).join("; ");
        }
      }
      if (!errMsg) {
        if (response.status === 401) {
          errMsg = "Incorrect email or password. Please try again.";
        } else if (response.status === 403) {
          errMsg = "You do not have permission to perform this action.";
        } else if (response.status === 404) {
          errMsg = "The requested resource was not found.";
        } else if (response.status === 429) {
          errMsg = "Too many requests. Please wait a moment before trying again.";
        } else if (response.status >= 500) {
          errMsg = "Server error occurred. Please try again shortly.";
        } else {
          errMsg = "Request failed. Please try again.";
        }
      }
      const err = new Error(errMsg);
      err.status = response.status;
      err.payload = payload;
      throw err;
    }
    return payload ? payload.data : null;
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
