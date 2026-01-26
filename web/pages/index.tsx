import { useEffect, useMemo, useState } from "react";

const API =
  process.env.NEXT_PUBLIC_VELU_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8010";

type AllowedResp = { ok: boolean; tasks: string[]; role?: string };
type PostTaskResp = { ok: boolean; job_id: number; received?: any };
type RecentResp = {
  ok: boolean;
  items: Array<{
    id: number;
    ts?: number;
    status?: string;
    task?: string;
    payload?: any;
    artifact_name?: string;
    artifact_path?: string;
    file_count?: number;
  }>;
};

function tierLabel(role: string | undefined | null) {
  const r = (role || "").toLowerCase();
  if (r === "admin") return { name: "superhero", badge: "Admin" };
  if (r === "builder") return { name: "hero", badge: "Builder" };
  if (r === "viewer") return { name: "base", badge: "Viewer" };
  return { name: "unknown", badge: "Unknown" };
}

async function apiGet<T>(path: string, apiKey: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (apiKey) headers["X-API-Key"] = apiKey;
  const res = await fetch(`${API}${path}`, { headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (body as any)?.detail || `HTTP ${res.status}`;
    throw new Error(String(msg));
  }
  return body as T;
}

async function apiPost<T>(path: string, apiKey: string, payload: any): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (body as any)?.detail || `HTTP ${res.status}`;
    throw new Error(String(msg));
  }
  return body as T;
}

export default function Home() {
  const [apiKey, setApiKey] = useState("");
  const [savedKey, setSavedKey] = useState("");

  const [allowed, setAllowed] = useState<string[]>([]);
  const [role, setRole] = useState<string>("");
  const tier = useMemo(() => tierLabel(role), [role]);

  const [task, setTask] = useState("plan");
  const [payloadText, setPayloadText] = useState(
    JSON.stringify({ idea: "build something useful" }, null, 2),
  );

  const [recent, setRecent] = useState<RecentResp["items"]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string>("");

  // load api key from localStorage
  useEffect(() => {
    const k = localStorage.getItem("velu_api_key") || "";
    setApiKey(k);
    setSavedKey(k);
  }, []);

  async function refreshAllowed(key: string) {
    const r = await apiGet<AllowedResp>("/tasks/allowed", key);
    setAllowed(Array.isArray(r.tasks) ? r.tasks : []);
    setRole(r.role || "");
    // pick something valid
    const nextTask = (r.tasks || []).includes(task) ? task : (r.tasks?.[0] || "plan");
    setTask(nextTask);
  }

  async function refreshRecent(key: string) {
    const r = await apiGet<RecentResp>("/tasks/recent?limit=20", key);
    setRecent(r.items || []);
  }

  useEffect(() => {
    if (!savedKey) {
      // no key: still try (dev mode may be open)
      refreshAllowed("").catch(() => {});
      refreshRecent("").catch(() => {});
      return;
    }
    refreshAllowed(savedKey).catch(() => {});
    refreshRecent(savedKey).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedKey]);

  const canSubmit = useMemo(() => {
    if (!allowed.length) return true; // permissive if server didn't return list
    return allowed.includes(task);
  }, [allowed, task]);

  async function saveKey() {
    const k = apiKey.trim();
    localStorage.setItem("velu_api_key", k);
    setSavedKey(k);
    setMsg("Saved API key.");
    setTimeout(() => setMsg(""), 1500);
  }

  async function clearKey() {
    localStorage.removeItem("velu_api_key");
    setApiKey("");
    setSavedKey("");
    setAllowed([]);
    setRole("");
    setMsg("Cleared API key.");
    setTimeout(() => setMsg(""), 1500);
  }

  async function submit() {
    setBusy(true);
    setMsg("");
    try {
      let payload: any = {};
      const raw = payloadText.trim();
      if (raw) payload = JSON.parse(raw);

      const res = await apiPost<PostTaskResp>("/tasks", savedKey, {
        task,
        payload,
      });

      setMsg(`Queued job #${res.job_id}`);
      await refreshRecent(savedKey);
    } catch (e: any) {
      setMsg(e?.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f8fafc",
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
      }}
    >
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "rgba(255,255,255,0.9)",
          backdropFilter: "blur(8px)",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "14px 16px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 12,
              background: "#0f172a",
              color: "white",
              display: "grid",
              placeItems: "center",
              fontWeight: 800,
            }}
          >
            V
          </div>
          <div style={{ lineHeight: 1.1 }}>
            <div style={{ fontWeight: 800, color: "#0f172a" }}>Velu Console</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>
              API: <code>{API}</code>
            </div>
          </div>

          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            <span
              style={{
                fontSize: 12,
                padding: "6px 10px",
                borderRadius: 999,
                border: "1px solid #e2e8f0",
                background: "white",
                color: "#0f172a",
                fontWeight: 700,
              }}
              title="Tier derived from role"
            >
              Tier: {tier.name} · {tier.badge}
            </span>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "18px 16px" }}>
        {/* API key card */}
        <section
          style={{
            background: "white",
            border: "1px solid #e5e7eb",
            borderRadius: 18,
            padding: 16,
            boxShadow: "0 6px 20px rgba(15, 23, 42, 0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "end", gap: 10, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 240 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#334155", marginBottom: 6 }}>
                API Key (X-API-Key)
              </div>
              <input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="k_base / k_hero / k_super …"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  outline: "none",
                }}
              />
              <div style={{ marginTop: 6, fontSize: 12, color: "#64748b" }}>
                Stored locally in your browser as <code>velu_api_key</code>.
              </div>
            </div>

            <button
              onClick={saveKey}
              style={{
                padding: "10px 14px",
                borderRadius: 14,
                border: "none",
                background: "#0f172a",
                color: "white",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Save
            </button>

            <button
              onClick={clearKey}
              style={{
                padding: "10px 14px",
                borderRadius: 14,
                border: "1px solid #e5e7eb",
                background: "white",
                color: "#0f172a",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Clear
            </button>

            <button
              onClick={() => {
                refreshAllowed(savedKey || "").catch(() => {});
                refreshRecent(savedKey || "").catch(() => {});
              }}
              style={{
                padding: "10px 14px",
                borderRadius: 14,
                border: "1px solid #e5e7eb",
                background: "#f8fafc",
                color: "#0f172a",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Refresh
            </button>
          </div>

          {msg ? (
            <div style={{ marginTop: 12, fontSize: 13, color: "#0f172a" }}>{msg}</div>
          ) : null}
        </section>

        {/* Submit task + recent */}
        <div
          style={{
            marginTop: 16,
            display: "grid",
            gap: 16,
            gridTemplateColumns: "1.1fr 0.9fr",
          }}
        >
          <section
            style={{
              background: "white",
              border: "1px solid #e5e7eb",
              borderRadius: 18,
              padding: 16,
              boxShadow: "0 6px 20px rgba(15, 23, 42, 0.04)",
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 900, color: "#334155" }}>Submit task</div>

            <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 800, color: "#334155", marginBottom: 6 }}>
                  Task
                </div>
                <select
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 12,
                    border: "1px solid #e5e7eb",
                    background: "white",
                  }}
                >
                  {(allowed.length ? allowed : ["plan", "chat", "ui_scaffold", "packager", "deploy"]).map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                {!canSubmit ? (
                  <div style={{ marginTop: 6, fontSize: 12, color: "#b91c1c" }}>
                    This task is not allowed for your tier.
                  </div>
                ) : null}
              </div>

              <div>
                <div style={{ fontSize: 12, fontWeight: 800, color: "#334155", marginBottom: 6 }}>
                  Payload (JSON)
                </div>
                <textarea
                  value={payloadText}
                  onChange={(e) => setPayloadText(e.target.value)}
                  rows={10}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 12,
                    border: "1px solid #e5e7eb",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    fontSize: 12,
                  }}
                />
              </div>

              <button
                onClick={submit}
                disabled={busy || !canSubmit}
                style={{
                  padding: "12px 14px",
                  borderRadius: 14,
                  border: "none",
                  background: busy || !canSubmit ? "#94a3b8" : "#0f172a",
                  color: "white",
                  fontWeight: 900,
                  cursor: busy || !canSubmit ? "not-allowed" : "pointer",
                }}
              >
                {busy ? "Submitting…" : "Submit"}
              </button>
            </div>
          </section>

          <section
            style={{
              background: "white",
              border: "1px solid #e5e7eb",
              borderRadius: 18,
              padding: 16,
              boxShadow: "0 6px 20px rgba(15, 23, 42, 0.04)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#334155" }}>Recent jobs</div>
              <a
                href={`${API}/docs`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 12, color: "#0f172a", fontWeight: 800, textDecoration: "none" }}
              >
                Open API docs
              </a>
            </div>

            <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
              {recent.length === 0 ? (
                <div style={{ fontSize: 13, color: "#64748b" }}>No jobs yet.</div>
              ) : (
                recent.map((j) => (
                  <div
                    key={j.id}
                    style={{
                      border: "1px solid #e5e7eb",
                      borderRadius: 14,
                      padding: 12,
                      background: "#f8fafc",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                      <div style={{ fontWeight: 900, color: "#0f172a" }}>#{j.id}</div>
                      <div style={{ fontSize: 12, color: "#334155", fontWeight: 800 }}>
                        {j.status || "unknown"}
                      </div>
                    </div>

                    <div style={{ marginTop: 6, fontSize: 12, color: "#334155" }}>
                      <strong>{j.task || "?"}</strong>
                    </div>

                    <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 8 }}>
                      <a
                        href={`${API}/results/${j.id}?expand=1`}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          fontSize: 12,
                          fontWeight: 900,
                          color: "#0f172a",
                          textDecoration: "none",
                          padding: "6px 10px",
                          borderRadius: 999,
                          border: "1px solid #e2e8f0",
                          background: "white",
                        }}
                      >
                        View result
                      </a>

                      {j.artifact_name ? (
                        <a
                          href={`${API}/artifacts/${encodeURIComponent(j.artifact_name)}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            fontSize: 12,
                            fontWeight: 900,
                            color: "#0f172a",
                            textDecoration: "none",
                            padding: "6px 10px",
                            borderRadius: 999,
                            border: "1px solid #e2e8f0",
                            background: "white",
                          }}
                        >
                          Download {j.artifact_name}
                        </a>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <footer style={{ marginTop: 18, fontSize: 12, color: "#64748b" }}>
          Tip: set <code>NEXT_PUBLIC_VELU_API_URL</code> to point to a remote Velu API.
        </footer>
      </div>
    </main>
  );
}
