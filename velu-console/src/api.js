// velu-console/src/api.js

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8010").replace(
  /\/+$/,
  ""
);

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      // later enable real API keys on 8010, add:
      // "X-API-Key": "dev",
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // "X-API-Key": "dev",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

/* ---------- i18n endpoints ---------- */

export const i18nApi = {
  getLocales() {
    return apiGet("/v1/i18n/locales");
  },

  getMessages(locale) {
    const params = new URLSearchParams({ locale });
    return apiGet(`/v1/i18n/messages?${params.toString()}`);
  },

  generateMessages(product) {
    // product: { name: string, locales: string[] }
    return apiPost("/v1/i18n/messages", { product });
  },

  translate(text, targetLocale) {
    return apiPost("/v1/i18n/translate", {
      text,
      target_locale: targetLocale,
    });
  },
};

/* ---------- Assistant intake ---------- */

export const assistantApi = {
  intake(payload) {
    // payload: { company: { name }, product: { type, goal, locales?, channels? }, idea }
    return apiPost("/v1/assistant/intake", payload);
  },
};

/* ---------- Tasks + results + artifacts ---------- */

export const tasksApi = {
  recent(limit = 20) {
    const params = new URLSearchParams({ limit: String(limit) });
    return apiGet(`/tasks/recent?${params.toString()}`);
  },

  getResult(jobId, expand = 0) {
    const params = new URLSearchParams({ expand: String(expand) });
    return apiGet(`/results/${jobId}?${params.toString()}`);
  },
};

export const artifactsApi = {
  url(name) {
    return `${API_BASE}/artifacts/${encodeURIComponent(name)}`;
  },
};
