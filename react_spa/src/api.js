const RAW_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function apiBase() {
  return RAW_BASE.replace(/\/+$/, "");
}

export function apiUrl(path) {
  const base = apiBase();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}
