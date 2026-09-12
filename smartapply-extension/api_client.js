// SmartApply Copilot - API Client

class SmartResumeAPI {
  constructor(baseUrl = "http://127.0.0.1:8000/api/v1") {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  setToken(token) {
    this.token = token;
  }

  async getHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async testConnection() {
    try {
      const res = await fetch("http://127.0.0.1:8000/health");
      return res.ok;
    } catch {
      return false;
    }
  }

  async getFieldAnswers(fields = []) {
    const headers = await this.getHeaders();
    const res = await fetch(`${this.baseUrl}/smartapply/field-answers`, {
      method: "POST",
      headers,
      body: JSON.stringify({ fields }),
    });
    if (!res.ok) throw new Error("Failed to fetch verified field answers");
    const json = await res.json();
    return json.data;
  }

  async detectJob(pageData) {
    const headers = await this.getHeaders();
    const res = await fetch(`${this.baseUrl}/smartapply/detect-job`, {
      method: "POST",
      headers,
      body: JSON.stringify(pageData),
    });
    if (!res.ok) throw new Error("Failed to analyze job details");
    const json = await res.json();
    return json.data;
  }

  async createApplication(appData) {
    const headers = await this.getHeaders();
    const res = await fetch(`${this.baseUrl}/applications`, {
      method: "POST",
      headers,
      body: JSON.stringify(appData),
    });
    if (!res.ok) throw new Error("Failed to save application");
    const json = await res.json();
    return json.data;
  }
}
