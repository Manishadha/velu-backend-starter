const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type ApiFetchOpts = RequestInit & { token?: string };

export async function apiFetch<T>(path: string, opts: ApiFetchOpts = {}): Promise<T> {
  const { token, headers, ...rest } = opts;

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      ...(headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) msg = `${msg}: ${data.detail}`;
      else msg = `${msg}: ${JSON.stringify(data).slice(0, 200)}`;
    } catch {
      const text = await res.text().catch(() => "");
      if (text) msg = `${msg}: ${text.slice(0, 200)}`;
    }
    throw new Error(msg);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string, token?: string) =>
  apiFetch<T>(path, { method: "GET", token });

export const apiPost = <T>(path: string, body: any, token?: string) =>
  apiFetch<T>(path, {
    method: "POST",
    token,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const apiPut = <T>(path: string, body: any, token?: string) =>
  apiFetch<T>(path, {
    method: "PUT",
    token,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const apiDelete = <T>(path: string, token?: string) =>
  apiFetch<T>(path, { method: "DELETE", token });
