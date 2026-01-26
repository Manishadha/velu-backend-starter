import { useEffect, useMemo, useState } from "react";
import "./app.css";
import { tasksApi, artifactsApi } from "./api";

// Prefer explicit Velu console env vars, but keep backward-compatible fallbacks.
const DEFAULT_API =
  import.meta.env.VITE_VELU_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8010";

const DEFAULT_KEY =
  import.meta.env.VITE_VELU_API_KEY ||
  localStorage.getItem("apiKey") ||
  "dev";

const PLAN_TIER_LABELS = {
  base: "Base — basic tasks",
  hero: "Hero — build & generate",
  superhero: "Superhero — everything",
};

const ASSISTANT_MODE_LABELS = {
  basic: "Basic (simple question flow)",
  pro: "Pro (richer spec + LLM assist)",
  architect: "Architect (multi-tenant / SaaS planning)",
};

const SECURITY_LABELS = {
  standard: "Standard",
  hardened: "Hardened (audit logs, IP allowlist, stricter defaults)",
};

const LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "nl", label: "Dutch" },
  { code: "de", label: "German" },
  { code: "es", label: "Spanish" },
  { code: "pt", label: "Portuguese" },
  { code: "pt-BR", label: "Portuguese (Brazil)" },
  { code: "it", label: "Italian" },
  { code: "ru", label: "Russian" },
  { code: "hi", label: "Hindi" },
  { code: "bn", label: "Bengali" },
  { code: "ur", label: "Urdu" },
  { code: "ar", label: "Arabic" },
  { code: "fa", label: "Persian (Farsi)" },
  { code: "tr", label: "Turkish" },
  { code: "zh-CN", label: "Chinese (Simplified)" },
  { code: "zh-TW", label: "Chinese (Traditional)" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "th", label: "Thai" },
  { code: "vi", label: "Vietnamese" },
  { code: "id", label: "Indonesian" },
  { code: "sw", label: "Swahili" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "ml", label: "Malayalam" },
  { code: "pa", label: "Punjabi" },
  { code: "pl", label: "Polish" },
  { code: "sv", label: "Swedish" },
  { code: "da", label: "Danish" },
  { code: "no", label: "Norwegian" },
  { code: "fi", label: "Finnish" },
  { code: "el", label: "Greek" },
  { code: "cs", label: "Czech" },
  { code: "ro", label: "Romanian" },
];

const POPULAR_LANGS = [
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "nl", label: "Dutch" },
  { code: "de", label: "German" },
  { code: "es", label: "Spanish" },
  { code: "pt-BR", label: "Portuguese (Brazil)" },
  { code: "hi", label: "Hindi" },
  { code: "ar", label: "Arabic" },
  { code: "zh-CN", label: "Chinese (Simplified)" },
  { code: "ja", label: "Japanese" },
];

const CONSOLE_LABELS = {
  en: {
    "app.title": "Velu Console",
    "header.health": "Health",
    "header.ui_language": "UI language",
    "tabs.queue": "Velu queue",
    "tabs.assistant": "Assistant",
    "tabs.help": "Help",
    "tabs.i18n": "Languages (i18n)",
  },
  fr: {
    "app.title": "Console Velu",
    "header.health": "Santé",
    "header.ui_language": "Langue UI",
    "tabs.queue": "File Velu",
    "tabs.assistant": "Assistant",
    "tabs.help": "Aide",
    "tabs.i18n": "Langues (i18n)",
  },
};

function getConsoleLabel(lang, key) {
  const table = CONSOLE_LABELS[lang] || CONSOLE_LABELS.en;
  return table[key] || CONSOLE_LABELS.en[key] || key;
}

function badgeColor(status) {
  if (status === "done") return "#12b981";
  if (status === "error") return "#ef4444";
  return "#f59e0b";
}

function Badge({ status }) {
  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 999,
        color: "#fff",
        background: badgeColor(status),
        fontSize: 12,
        textTransform: "lowercase",
      }}
    >
      {status}
    </span>
  );
}

function TabButton({ active, children, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 12px",
        borderRadius: 999,
        border: active ? "1px solid #111827" : "1px solid #e5e7eb",
        background: active ? "#111827" : "#f9fafb",
        color: active ? "#fff" : "#111827",
        fontSize: 13,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

/**
 * Single place to attach API key and do JSON.
 * - Adds X-API-Key to *all* requests (GET/POST)
 * - Returns parsed JSON or throws with helpful message
 */
function makeApiClient({ apiUrl, apiKey }) {
  const base = String(apiUrl || "").replace(/\/$/, "");

  async function request(path, opts = {}) {
    const url = `${base}${path.startsWith("/") ? "" : "/"}${path}`;

    const headers = {
      ...(opts.headers || {}),
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
    };

    const r = await fetch(url, { ...opts, headers });

    // Try to parse JSON even for errors (FastAPI style)
    let data = null;
    const text = await r.text();
    if (text && text.trim()) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }
    } else {
      data = {};
    }

    if (!r.ok) {
      const detail =
        (data && data.detail) ||
        (typeof data?.raw === "string" ? data.raw : "") ||
        `HTTP ${r.status}`;
      const err = new Error(detail);
      err.status = r.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  return {
    get: (path) => request(path, { method: "GET" }),
    post: (path, body) =>
      request(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      }),
  };
}

function FileCard({ f }) {
  return (
    <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 8 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 6,
        }}
      >
        <code>{f.path}</code>
        <button
          onClick={() => navigator.clipboard.writeText(f.content || "")}
          title="Copy content"
          style={{ padding: "4px 8px", fontSize: 12 }}
        >
          Copy
        </button>
      </div>
      <pre
        style={{
          background: "#e0f2fe",
          color: "#0f172a",
          padding: 8,
          borderRadius: 6,
          maxHeight: 220,
          overflow: "auto",
          fontSize: 12,
        }}
      >
        {f.content}
      </pre>
    </div>
  );
}

function Subjobs({ result }) {
  const subs = result?.result?.subjobs || {};
  const details = result?.result?.subjobs_detail || null;
  const names = Object.keys(subs);
  if (names.length === 0) return null;

  return (
    <div style={{ marginTop: 12 }}>
      <h4 style={{ margin: "8px 0" }}>Subjobs</h4>
      <div style={{ display: "grid", gap: 8 }}>
        {names.map((name) => {
          const jid = subs[name];
          const d = details?.[name];
          const st = typeof d === "object" && d ? d.status || "?" : "…";
          return (
            <div
              key={name}
              style={{ border: "1px solid #eee", borderRadius: 8, padding: 8 }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 6,
                }}
              >
                <div>
                  <strong>{name}</strong> &nbsp; <code>#{jid}</code>
                </div>
                <div>
                  <span style={{ fontSize: 12, opacity: 0.75 }}>{st}</span>
                </div>
              </div>
              {d && (
                <pre
                  style={{
                    background: "#e0f2fe",
                    color: "#0f172a",
                    padding: 8,
                    borderRadius: 6,
                    maxHeight: 220,
                    overflow: "auto",
                    fontSize: 12,
                  }}
                >
                  {JSON.stringify(d, null, 2)}
                </pre>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RepoSummaryView({ result }) {
  const summary = result?.result;
  if (!summary?.stats) return null;

  const { total_files_seen, by_ext = {}, top_dirs = {}, focus_dirs = {} } =
    summary.stats;

  const topDirsList = Object.entries(top_dirs)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const topExtList = Object.entries(by_ext)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const focusList = Object.entries(focus_dirs || {}).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ marginTop: 16 }}>
      <h4 style={{ margin: "8px 0" }}>Repo summary</h4>
      <p style={{ margin: "4px 0 12px" }}>
        <strong>Total files:</strong> {total_files_seen}
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          alignItems: "flex-start",
        }}
      >
        <div>
          <h5 style={{ margin: "4px 0" }}>Top directories</h5>
          <ul style={{ paddingLeft: 18, margin: 0, fontSize: 13 }}>
            {topDirsList.map(([dir, count]) => (
              <li key={dir}>
                <code>{dir}</code> — {count} files
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h5 style={{ margin: "4px 0" }}>Top extensions</h5>
          <ul style={{ paddingLeft: 18, margin: 0, fontSize: 13 }}>
            {topExtList.map(([ext, count]) => (
              <li key={ext}>
                <code>{ext}</code> — {count} files
              </li>
            ))}
          </ul>
        </div>
      </div>

      {focusList.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h5 style={{ margin: "4px 0" }}>Focused directories</h5>
          <ul style={{ paddingLeft: 18, margin: 0, fontSize: 13 }}>
            {focusList.map(([dir, count]) => (
              <li key={dir}>
                <code>{dir}</code> — {count} files
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/**
 * Assistant panel: talks to /assistant-chat on 8010
 */
function AssistantPanel({ api, apiKey }) {
  const [sessionId, setSessionId] = useState("velu_default");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("collecting");
  const [spec, setSpec] = useState({});
  const [jobs, setJobs] = useState({});
  const [history, setHistory] = useState([]);
  const [lastJobId, setLastJobId] = useState(null);
  const [initialized, setInitialized] = useState(false);
  const [backendChoice, setBackendChoice] = useState("rules");
  const [useRepoSummary, setUseRepoSummary] = useState(false);
  const [repoRoot, setRepoRoot] = useState(".");
  const [repoFocusDirs, setRepoFocusDirs] = useState("services,agents,tests");


  async function pollJob(jobId) {
    let keep = true;
    while (keep) {
      const d = await api.get(`/results/${jobId}?expand=1`);
      const item = d.item || d;
      const res = item.result || {};
      setStage(res.stage || item.status || "collecting");
      setSpec(res.spec || {});
      setJobs(res.jobs || {});
      setHistory(res.history_tail || []);
      const s = (item.status || "").toLowerCase();
      if (s === "done" || s === "error") {
        keep = false;
      } else {
        await new Promise((resFn) => setTimeout(resFn, 800));
      }
    }
  }

  async function sendToBackend(message, { reset = false, sessionOverride } = {}) {
    setSending(true);
    setError("");
    try {
      const sid = sessionOverride || sessionId || "velu_default";
      const body = {
        message: message ?? "",
        session_id: sid,
        backend: backendChoice || "rules",
        use_repo_summary: useRepoSummary,
        repo_root: repoRoot,
        repo_focus_dirs: repoFocusDirs
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
      };
      if (reset) body.reset = true;

      const data = await api.post("/assistant-chat", body);
      const jobId = data.job_id;
      setLastJobId(jobId);
      await pollJob(jobId);
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!initialized) {
      setInitialized(true);
      sendToBackend("", { reset: false }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialized, sessionId]);

  function onSubmit(e) {
    e?.preventDefault?.();
    if (!input.trim()) return;
    setHistory((old) => [
      ...old,
      { role: "user", content: input, ts: Date.now() / 1000 },
    ]);
    const msg = input;
    setInput("");
    sendToBackend(msg, { reset: false });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit(e);
    }
  }

  async function handleReset() {
    const newId = `project_${Date.now()}`;
    setSessionId(newId);
    setHistory([]);
    setSpec({});
    setJobs({});
    setStage("collecting");
    setLastJobId(null);
    setError("");
    setInitialized(false);
    await sendToBackend("", { reset: true, sessionOverride: newId });
  }

  async function handleBuildNow() {
    await sendToBackend("build", { reset: false });
  }

  const specEntries = Object.entries(spec || {});
  const planTier = spec.plan_tier || "base";
  const assistantMode = spec.assistant_mode || "basic";
  const securityPosture = spec.security_posture || "standard";

  return (
    <div style={{ border: "1px solid #e5e7eb", padding: 16, borderRadius: 12 }}>
      <h2 style={{ marginTop: 0, marginBottom: 4 }}>Velu Assistant</h2>
      <p style={{ marginTop: 0, fontSize: 13, color: "#4b5563" }}>
        Describe in simple words what is needed. Velu will ask a few questions
        and then build the app or website.
      </p>

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginTop: 8,
          marginBottom: 8,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", minWidth: 200 }}>
          <label>Session ID</label>
          <input
            value={sessionId}
            onChange={(e) => {
              setSessionId(e.target.value || "velu_default");
              setInitialized(false);
              setHistory([]);
              setSpec({});
              setJobs({});
              setStage("collecting");
              setLastJobId(null);
            }}
            placeholder="velu_default"
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span style={{ fontSize: 12, color: "#6b7280" }}>Backend</span>
          <div style={{ display: "flex", gap: 6 }}>
            <TabButton
              active={backendChoice === "rules"}
              onClick={() => setBackendChoice("rules")}
            >
              Rules
            </TabButton>
            <TabButton
              active={backendChoice === "local_llm"}
              onClick={() => setBackendChoice("local_llm")}
            >
              Local LLM
            </TabButton>
            <TabButton
              active={backendChoice === "remote_llm"}
              onClick={() => setBackendChoice("remote_llm")}
            >
              Remote LLM
            </TabButton>
          </div>
        </div>

        <div style={{ fontSize: 13, color: "#4b5563" }}>
          <div>
            <strong>Stage:</strong> {stage || "collecting"}
          </div>
          {lastJobId && (
            <div>
              <strong>Last job:</strong> #{lastJobId}
            </div>
          )}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={handleReset}
            disabled={sending}
            className="ghost"
          >
            New project
          </button>
          <button type="button" onClick={handleBuildNow} disabled={sending}>
            Build now
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            margin: "8px 0",
            padding: "8px 12px",
            borderRadius: 8,
            background: "#FEF2F2",
            color: "#991B1B",
            border: "1px solid #FCA5A5",
            fontSize: 14,
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: 16,
          alignItems: "flex-start",
        }}
      >
        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: 10,
            padding: 10,
            minHeight: 260,
            maxHeight: 420,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: 4,
              marginBottom: 8,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            {history.length === 0 && (
              <div style={{ fontSize: 13, color: "#6b7280", padding: 8 }}>
                The assistant will appear here. For example:
                <em> "I want a simple website to show my products"</em>.
              </div>
            )}
            {history.map((m, idx) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    justifyContent: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      maxWidth: "80%",
                      padding: "6px 10px",
                      borderRadius: 12,
                      fontSize: 14,
                      whiteSpace: "pre-wrap",
                      background: isUser ? "#111827" : "#e0f2fe",
                      color: isUser ? "#ffffff" : "#0f172a",
                    }}
                  >
                    {m.content}
                  </div>
                </div>
              );
            })}
            {sending && (
              <div style={{ fontSize: 12, color: "#6b7280", padding: 4 }}>
                Thinking…
              </div>
            )}
          </div>

          <form onSubmit={onSubmit} style={{ marginTop: "auto" }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Describe what is needed…"
              style={{ width: "100%", resize: "vertical", marginBottom: 6 }}
              disabled={sending}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span style={{ fontSize: 11, color: "#6b7280" }}>
                Tip: type <code>build</code> when the plan looks good.
              </span>
              <button
                type="submit"
                disabled={sending || !input.trim()}
                style={{ minWidth: 90 }}
              >
                {sending ? "Sending…" : "Send"}
              </button>
            </div>
          </form>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={useRepoSummary}
              onChange={(e) => setUseRepoSummary(e.target.checked)}
            />
            Use repo context (repo_summary)
          </label>

          {useRepoSummary && (
            <>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: 12, color: "#6b7280" }}>Repo root</span>
                <input value={repoRoot} onChange={(e) => setRepoRoot(e.target.value)} />
              </div>

              <div style={{ display: "flex", flexDirection: "column", minWidth: 260 }}>
                <span style={{ fontSize: 12, color: "#6b7280" }}>Focus dirs (comma)</span>
                <input
                    value={repoFocusDirs}
                    onChange={(e) => setRepoFocusDirs(e.target.value)}
                    placeholder="services,agents,tests"
                />
              </div>
            </>
          )}
        </div>

        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: 10,
            padding: 10,
            fontSize: 13,
          }}
        >
          <h3 style={{ marginTop: 0, fontSize: 15 }}>Product summary</h3>
          {specEntries.length === 0 ? (
            <p style={{ margin: "4px 0 6px", fontSize: 13, color: "#4b5563" }}>
              <strong>Plan:</strong> {PLAN_TIER_LABELS[planTier] || planTier}
              {" · "}
              <strong>Assistant:</strong>{" "}
              {ASSISTANT_MODE_LABELS[assistantMode] || assistantMode}
              {" · "}
              <strong>Security:</strong>{" "}
              {SECURITY_LABELS[securityPosture] || securityPosture}
            </p>
          ) : (
            <ul style={{ paddingLeft: 18, margin: 0 }}>
              {specEntries.map(([k, v]) => {
                const asString = Array.isArray(v) ? v.join(", ") : String(v || "");
                let displayValue = asString;
                if (k === "assistant_mode") {
                  displayValue = ASSISTANT_MODE_LABELS[asString] || asString;
                } else if (k === "security_posture") {
                  displayValue = SECURITY_LABELS[asString] || asString;
                } else if (k === "plan_tier") {
                  displayValue = PLAN_TIER_LABELS[asString] || asString;
                }
                return (
                  <li key={k} style={{ marginBottom: 2 }}>
                    <strong>{k}:</strong> {displayValue}
                  </li>
                );
              })}
            </ul>
          )}

          {Object.keys(jobs || {}).length > 0 && (
            <div style={{ marginTop: 10 }}>
              <h4 style={{ margin: "4px 0", fontSize: 14 }}>Related jobs</h4>
              <ul style={{ paddingLeft: 18, margin: 0 }}>
                {Object.entries(jobs).map(([name, jid]) => (
                  <li key={name}>
                    {name}: <code>#{jid}</code>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function I18nPanel({ api }) {
  const [serverLocales, setServerLocales] = useState([]);
  const [loadingLocales, setLoadingLocales] = useState(false);
  const [error, setError] = useState("");

  const [localePreview, setLocalePreview] = useState("en");
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [productName, setProductName] = useState("Velu application");
  const [targetLocalesInput, setTargetLocalesInput] = useState("en,fr,nl,de,ar,ta");
  const [generated, setGenerated] = useState(null);
  const [generateLoading, setGenerateLoading] = useState(false);

  const [translateText, setTranslateText] = useState("Bonjour");
  const [translateTarget, setTranslateTarget] = useState("en");
  const [translateResult, setTranslateResult] = useState(null);
  const [translateLoading, setTranslateLoading] = useState(false);

  useEffect(() => {
    async function loadLocales() {
      setLoadingLocales(true);
      setError("");
      try {
        const data = await api.get("/v1/i18n/locales");
        const locs = Array.isArray(data.locales)
          ? data.locales
          : Object.values(data.locales || {});
        setServerLocales(locs);
      } catch (e) {
        setError(`Failed to load locales: ${String(e?.message || e)}`);
      } finally {
        setLoadingLocales(false);
      }
    }
    loadLocales().catch(() => {});
  }, [api]);

  function syncFromPopular(code) {
    const current = targetLocalesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const exists = current.includes(code);
    const next = exists ? current.filter((c) => c !== code) : [...current, code];
    setTargetLocalesInput(next.join(","));
  }

  async function handlePreviewMessages(e) {
    e?.preventDefault?.();
    setPreviewLoading(true);
    setError("");
    setPreviewData(null);
    try {
      const data = await api.get(
        `/v1/i18n/messages?locale=${encodeURIComponent(localePreview)}`
      );
      setPreviewData(data);
    } catch (e) {
      setError(`Preview failed: ${String(e?.message || e)}`);
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleGenerateMessages(e) {
    e?.preventDefault?.();
    setGenerateLoading(true);
    setError("");
    setGenerated(null);
    try {
      const locales = targetLocalesInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const payload = { product: { name: productName.trim() || "Product", locales } };
      const data = await api.post("/v1/i18n/messages", payload);
      setGenerated(data);
    } catch (e) {
      setError(`Generate failed: ${String(e?.message || e)}`);
    } finally {
      setGenerateLoading(false);
    }
  }

  async function handleTranslate(e) {
    e?.preventDefault?.();
    setTranslateLoading(true);
    setError("");
    setTranslateResult(null);
    try {
      const payload = { text: translateText, target_locale: translateTarget };
      const data = await api.post("/v1/i18n/translate", payload);
      setTranslateResult(data);
    } catch (e) {
      setError(`Translate failed: ${String(e?.message || e)}`);
    } finally {
      setTranslateLoading(false);
    }
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Languages (i18n)</h2>
      <p className="muted">
        This tab talks to <code>/v1/i18n/*</code> on the Velu API.
      </p>

      {error && (
        <div
          style={{
            margin: "8px 0",
            padding: "8px 12px",
            borderRadius: 8,
            background: "#FEF2F2",
            color: "#991B1B",
            border: "1px solid #FCA5A5",
            fontSize: 14,
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="grid-2">
        <section>
          <h3>Available locales (server)</h3>
          {loadingLocales ? (
            <p>Loading locales…</p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
              {serverLocales.map((loc) => (
                <span
                  key={loc}
                  style={{
                    padding: "4px 8px",
                    borderRadius: 999,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                    background: "#f9fafb",
                  }}
                >
                  {loc}
                </span>
              ))}
              {serverLocales.length === 0 && (
                <span className="muted" style={{ fontSize: 12 }}>
                  No locales from server (or request failed).
                </span>
              )}
            </div>
          )}

          <h3>Preview messages for one locale</h3>
          <form onSubmit={handlePreviewMessages}>
            <label>Locale to preview</label>
            <input
              value={localePreview}
              onChange={(e) => setLocalePreview(e.target.value)}
              placeholder="en, fr, nl…"
            />
            <button
              type="submit"
              disabled={previewLoading || !localePreview.trim()}
              style={{ marginTop: 8 }}
            >
              {previewLoading ? "Loading…" : "Preview messages"}
            </button>
          </form>

          {previewData && (
            <div style={{ marginTop: 8 }}>
              <pre>{JSON.stringify(previewData, null, 2)}</pre>
            </div>
          )}
        </section>

        <section>
          <h3>Generate product messages</h3>
          <form onSubmit={handleGenerateMessages}>
            <label>Product / app name</label>
            <input
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="Velu application"
            />

            <label style={{ marginTop: 8 }}>Target locales (comma separated)</label>
            <input
              value={targetLocalesInput}
              onChange={(e) => setTargetLocalesInput(e.target.value)}
              placeholder="en,fr,es,pt-BR,hi,zh-CN,ja,ar"
            />

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {POPULAR_LANGS.map((lang) => {
                const codes = targetLocalesInput
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean);
                const active = codes.includes(lang.code);
                return (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => syncFromPopular(lang.code)}
                    style={{
                      padding: "4px 8px",
                      borderRadius: 999,
                      border: active ? "1px solid #111827" : "1px solid #e5e7eb",
                      background: active ? "#111827" : "#ffffff",
                      color: active ? "#ffffff" : "#111827",
                      fontSize: 11,
                    }}
                  >
                    {lang.label} ({lang.code})
                  </button>
                );
              })}
            </div>

            <button type="submit" disabled={generateLoading} style={{ marginTop: 10 }}>
              {generateLoading ? "Generating…" : "Generate messages"}
            </button>
          </form>

          {generated && (
            <div style={{ marginTop: 8 }}>
              <h4>Result</h4>
              <pre>{JSON.stringify(generated, null, 2)}</pre>
            </div>
          )}

          <h3 style={{ marginTop: 16 }}>Quick translate</h3>
          <form onSubmit={handleTranslate}>
            <label>Text to translate</label>
            <textarea
              rows={2}
              value={translateText}
              onChange={(e) => setTranslateText(e.target.value)}
              style={{ resize: "vertical" }}
            />
            <label style={{ marginTop: 8 }}>Target locale</label>
            <input
              value={translateTarget}
              onChange={(e) => setTranslateTarget(e.target.value)}
              placeholder="en, fr, es, de…"
            />
            <button
              type="submit"
              disabled={translateLoading || !translateText.trim()}
              style={{ marginTop: 8 }}
            >
              {translateLoading ? "Translating…" : "Translate"}
            </button>
          </form>

          {translateResult && (
            <div style={{ marginTop: 8 }}>
              <pre>{JSON.stringify(translateResult, null, 2)}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

/**
 * Quick intake wizard (submits a normal /tasks "intake" job)
 */
function IntakeWizard({ onSubmit, busy }) {
  const [kind, setKind] = useState("website");
  const [idea, setIdea] = useState("Company landing with contact form");

  const [frontend, setFrontend] = useState("nextjs");
  const [backend, setBackend] = useState("fastapi");
  const [database, setDatabase] = useState("sqlite");

  const [moduleName, setModuleName] = useState("hello_mod");

  const [selectedLangs, setSelectedLangs] = useState(["en", "fr", "nl", "de", "ar", "ta"]);
  const [langPickerOpen, setLangPickerOpen] = useState(false);

  function toggleLang(code) {
    setSelectedLangs((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  function useCommonSet() {
    setSelectedLangs(["en", "fr", "nl", "de", "ar", "ta"]);
  }

  function clearLangs() {
    setSelectedLangs([]);
  }

  async function submit() {
    const uiLanguages = selectedLangs.length ? selectedLangs : ["en"];
    const payload = {
      kind,
      idea,
      frontend,
      backend,
      database,
      module: moduleName,
      schema: {},
      ui_languages: uiLanguages,
    };
    await onSubmit(payload);
  }

  const selectedLabel =
    selectedLangs.length === 0
      ? "No languages selected yet"
      : selectedLangs
          .map((code) => {
            const opt = LANGUAGE_OPTIONS.find((o) => o.code === code);
            return opt ? `${opt.label} (${opt.code})` : code;
          })
          .join(", ");

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Quick Start Wizard</h3>
      <p className="muted" style={{ marginTop: 4 }}>
        Describe what you want, choose tech stack and UI languages.
      </p>

      <label>What are we building?</label>
      <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ marginBottom: 8 }}>
        <option value="website">Website</option>
        <option value="web_app">Web app</option>
        <option value="mobile_app">Mobile app</option>
        <option value="dashboard">Dashboard</option>
        <option value="api_only">API only (backend)</option>
      </select>

      <label>Idea (plain language)</label>
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        rows={2}
        style={{ resize: "vertical" }}
      />

      <div className="grid-3" style={{ marginTop: 8 }}>
        <div>
          <label>Frontend</label>
          <select value={frontend} onChange={(e) => setFrontend(e.target.value)}>
            <option value="nextjs">Next.js (React)</option>
            <option value="react">React SPA (Vite)</option>
            <option value="vue">Vue</option>
            <option value="sveltekit">SvelteKit</option>
            <option value="react_native">React Native</option>
            <option value="expo">Expo (React Native)</option>
            <option value="flutter">Flutter</option>
            <option value="tauri">Tauri (desktop)</option>
            <option value="none">None / API only</option>
          </select>
        </div>

        <div>
          <label>Backend</label>
          <select value={backend} onChange={(e) => setBackend(e.target.value)}>
            <option value="fastapi">FastAPI (Python)</option>
            <option value="django">Django (Python)</option>
            <option value="express">Express (Node)</option>
            <option value="nestjs">NestJS (Node)</option>
            <option value="node">Node (generic)</option>
            <option value="none">None (frontend only)</option>
          </select>
        </div>

        <div>
          <label>Database</label>
          <select value={database} onChange={(e) => setDatabase(e.target.value)}>
            <option value="sqlite">SQLite</option>
            <option value="postgres">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="mongodb">MongoDB</option>
            <option value="none">No database</option>
          </select>
        </div>
      </div>

      <label style={{ marginTop: 8 }}>UI languages</label>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => setLangPickerOpen((v) => !v)}
          style={{ fontSize: 13, padding: "6px 10px" }}
          disabled={busy}
        >
          {langPickerOpen ? "Hide languages" : "Choose languages"}
        </button>
        <span style={{ fontSize: 12, color: "#4b5563" }}>{selectedLabel}</span>
      </div>

      {langPickerOpen && (
        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            padding: 8,
            maxHeight: 220,
            overflow: "auto",
            marginTop: 6,
            background: "#ffffff",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: "#6b7280" }}>
              Choose any languages your client needs
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <button type="button" onClick={useCommonSet} style={{ fontSize: 11, padding: "4px 8px" }}>
                Common set
              </button>
              <button type="button" onClick={clearLangs} style={{ fontSize: 11, padding: "4px 8px" }}>
                Clear
              </button>
            </div>
          </div>

          {LANGUAGE_OPTIONS.map((opt) => (
            <label
              key={opt.code}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 13,
                marginBottom: 4,
              }}
            >
              <input
                type="checkbox"
                checked={selectedLangs.includes(opt.code)}
                onChange={() => toggleLang(opt.code)}
                style={{ width: "auto" }}
              />
              <span>
                {opt.label} <span style={{ opacity: 0.7 }}>({opt.code})</span>
              </span>
            </label>
          ))}
        </div>
      )}

      <label style={{ marginTop: 8 }}>Module/package name</label>
      <input value={moduleName} onChange={(e) => setModuleName(e.target.value)} />

      <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
        <button onClick={submit} disabled={busy}>
          {busy ? "Submitting…" : "Start pipeline"}
        </button>
      </div>
    </div>
  );
}

function HelpPanel() {
  return (
    <div className="card">
      <h2>How to use Velu</h2>

      <h3>Ports</h3>
      <ul>
        <li>
          <strong>Velu API</strong> — <code>http://127.0.0.1:8010</code>
        </li>
        <li>
          <strong>Velu console</strong> — <code>http://127.0.0.1:5178</code>
        </li>
      </ul>

      <pre>
        cd ~/Downloads/velu
        source .venv/bin/activate

        # worker
        export VELU_ENABLE_PACKAGER=1
        python -m services.worker.main

        # API
        export TASK_DB="$PWD/data/jobs.db"
        export API_KEYS="dev"
        uvicorn services.app_server.main:create_app --factory --port 8010

        # console
        cd velu-console
        npm install
        npm run dev -- --host 127.0.0.1 --port 5178
      </pre>
    </div>
  );
}

/**
 * Autodev panel
 */
function AutodevPanel({ onRun, busy }) {
  const [idea, setIdea] = useState("Improve hello_mod and fix tests");
  const [moduleName, setModuleName] = useState("hello_mod");
  const [maxCycles, setMaxCycles] = useState(3);
  const [runTests, setRunTests] = useState(true);

  async function handleRun() {
    await onRun({
      idea,
      module: moduleName,
      max_cycles: maxCycles,
      tests: runTests,
    });
  }

  return (
    <section
      style={{
        border: "1px solid #e5e7eb",
        padding: 16,
        borderRadius: 12,
        marginBottom: 16,
      }}
    >
      <h2 style={{ marginTop: 0 }}>Autodev</h2>
      <p className="muted" style={{ marginTop: 4 }}>
        Runs the autodev agent.
      </p>

      <label>Idea / goal</label>
      <textarea value={idea} onChange={(e) => setIdea(e.target.value)} rows={2} style={{ resize: "vertical" }} />

      <label style={{ marginTop: 8 }}>Module name</label>
      <input value={moduleName} onChange={(e) => setModuleName(e.target.value)} />

      <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
        <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span>Max cycles</span>
          <input
            type="number"
            min={1}
            max={10}
            value={maxCycles}
            onChange={(e) => setMaxCycles(Number(e.target.value) || 1)}
            style={{ width: 70 }}
          />
        </label>

        <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input type="checkbox" checked={runTests} onChange={(e) => setRunTests(e.target.checked)} />
          run tests
        </label>
      </div>

      <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
        <button onClick={handleRun} disabled={busy}>
          {busy ? "Running autodev…" : "Run autodev"}
        </button>
      </div>
    </section>
  );
}

/**
 * Main App
 */
export default function App() {
  const [apiUrl, setApiUrl] = useState(localStorage.getItem("apiUrl") || DEFAULT_API);

  // Prefer env key, then saved key, otherwise empty (works for open + tiers)
  const [apiKey, setApiKey] = useState(
    import.meta.env.VITE_VELU_API_KEY || localStorage.getItem("apiKey") || ""
  );

  // Recreate API helper whenever url/key changes
  const api = useMemo(() => makeApiClient({ apiUrl, apiKey }), [apiUrl, apiKey]);

  const [tab, setTab] = useState("queue");
  const [health, setHealth] = useState(null);

  const [allowedInfo, setAllowedInfo] = useState(null); // { ok, role?, tier?, tasks: [] }
  const [allowedError, setAllowedError] = useState("");

  // ✅ Fix: currentPlan must exist (or React will crash)
  //  keep it as a simple label like "base|hero|superhero".
  const [currentPlan, setCurrentPlan] = useState("base");

  const [task, setTask] = useState("plan");
  const [idea, setIdea] = useState("demo");
  const [moduleName, setModuleName] = useState("hello_mod");

  const [repoRoot, setRepoRoot] = useState(".");
  const [includeSnippets, setIncludeSnippets] = useState(true);
  const [useFocusDirs, setUseFocusDirs] = useState(true);
  const [focusDirs, setFocusDirs] = useState("src,services,agents,tests");

  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState(null);
  const [rawMode, setRawMode] = useState(false);

  const [recent, setRecent] = useState([]);
  const [watching, setWatching] = useState(false);
  const [recentLoading, setRecentLoading] = useState(false);
  const [recentError, setRecentError] = useState("");

  const [activeTab, setActiveTab] = useState("quick");

  const [consoleLang, setConsoleLang] = useState(localStorage.getItem("consoleLang") || "en");
  const t = (key) => getConsoleLabel(consoleLang, key);

  // Persist apiUrl/apiKey/lang
  useEffect(() => localStorage.setItem("apiUrl", apiUrl), [apiUrl]);
  useEffect(() => localStorage.setItem("apiKey", apiKey), [apiKey]);
  useEffect(() => localStorage.setItem("consoleLang", consoleLang), [consoleLang]);

  // ✅ Client-side gate for task dropdown/buttons.
  // - If allowedInfo not loaded yet, allow everything (so open mode never "locks" the UI).
  // - If loaded, allow only tasks in allowedInfo.tasks.
  function isTaskAllowedClientSide(name) {
    const list = allowedInfo?.tasks;
    if (!Array.isArray(list) || list.length === 0) return true;
    return list.includes(name);
  }

  // ✅ Load /health + /tasks/allowed whenever url/key changes
  useEffect(() => {
    // health
    fetch(`${apiUrl}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null));

    // allowed tasks (tiers/roles mode will enforce key; open mode usually returns ok/tasks anyway)
    (async () => {
      try {
        setAllowedError("");
        const info = await api.get("/tasks/allowed");
        setAllowedInfo(info);

        // Try to infer a plan label if server provides one; otherwise keep "base".
        // (This keeps UI stable across open + tiers deployments.)
        const inferred =
          info?.plan_tier ||
          info?.tier ||
          info?.role || // some servers use role names like base/hero/superhero
          null;

        if (typeof inferred === "string" && inferred.trim()) {
          setCurrentPlan(inferred.trim());
        } else {
          setCurrentPlan("base");
        }
      } catch (e) {
        setAllowedInfo(null);
        setAllowedError(String(e?.message || e));
        setCurrentPlan("base");
      }
    })();
  }, [apiUrl, apiKey, api]); // api changes when apiUrl/apiKey changes

  // ---- helper: fetch recent ----
  async function refreshRecent({ silent = false } = {}) {
    if (!silent) {
      setRecentLoading(true);
      setRecentError("");
    }

    try {
      const r = await fetch(`${apiUrl}/tasks/recent`, {
        headers: apiKey ? { "X-API-Key": apiKey } : undefined,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setRecent(d.items ?? []);
    } catch (e) {
      console.error("Failed to refresh recent tasks", e);
      if (!silent) setRecentError(String(e?.message || e));
    } finally {
      if (!silent) setRecentLoading(false);
    }
  }

  // ---- auto-refresh recent ----
  useEffect(() => {
    refreshRecent({ silent: true }).catch(() => {});
    const iv = setInterval(() => {
      refreshRecent({ silent: true }).catch(() => {});
    }, 1500);
    return () => clearInterval(iv);
  }, [apiUrl, apiKey]);

  // ---- task polling ----
  async function pollOnce(id) {
    const r = await fetch(`${apiUrl}/results/${id}?expand=1`, {
      headers: apiKey ? { "X-API-Key": apiKey } : undefined,
    });
    const d = await r.json();
    return d.item || d;
  }

  async function autoPoll(id) {
    let keep = true;
    while (keep) {
      const item = await pollOnce(id);
      setResult(item);
      const status = item?.status;
      if (status === "done" || status === "error") {
        keep = false;
        setWatching(false);
      } else {
        await new Promise((res) => setTimeout(res, 800));
      }
    }
  }

  async function enqueue(taskName, payload) {
    const r = await fetch(`${apiUrl}/tasks`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(apiKey ? { "X-API-Key": apiKey } : {}),
      },
      body: JSON.stringify({ task: taskName, payload }),
    });

    const d = await r.json();
    const id = String(d.job_id || "");
    setJobId(id);
    setResult(null);

    if (id) {
      setWatching(true);
      autoPoll(id);
    }
  }

  // ✅ Intake wizard submit (in UI calls submitIntake)
  async function submitIntake(payload) {
    if (!isTaskAllowedClientSide("intake")) {
      setAllowedError("Task 'intake' is not allowed by the server.");
      return;
    }
    await enqueue("intake", payload);
  }

  // ✅ Autodev submit (in UI calls submitAutodev)
  async function submitAutodev(payload) {
    if (!isTaskAllowedClientSide("autodev")) {
      setAllowedError("Task 'autodev' is not allowed by the server.");
      return;
    }
    await enqueue("autodev", payload);
  }

  // ---- manual submit ----
  async function submitTask() {
    // ✅ IMPORTANT: repo_summary does NOT exist in the backend /tasks/allowed.
    // So block it here to prevent confusing failures.
    if (task === "repo_summary") {
      setAllowedError(
        "repo_summary is not exposed by the worker (not in /tasks/allowed). Remove it from the UI or implement a worker handler."
      );
      return;
    }

    if (!isTaskAllowedClientSide(task)) {
      setAllowedError(`Task '${task}' is not allowed by the server.`);
      return;
    }

    const payload = { idea, module: moduleName };
    await enqueue(task, payload);
  }

  async function poll() {
    if (!jobId) return;
    setWatching(true);
    await autoPoll(jobId);
  }

  async function retryLast() {
    if (!result) return;
    const lastTask = result.task;
    const lastPayload = result.payload || {};
    if (!isTaskAllowedClientSide(lastTask)) {
      setAllowedError(`Task '${lastTask}' is not allowed by the server.`);
      return;
    }
    await enqueue(lastTask, lastPayload);
  }

  const pretty = useMemo(() => (result ? JSON.stringify(result, null, 2) : ""), [result]);

  const files = useMemo(() => {
    if (!result) return [];
    const f = result?.result?.files;
    return Array.isArray(f) ? f : [];
  }, [result]);

  const errorText =
    result?.result?.error ??
    (typeof result?.last_error === "string" ? result.last_error : result?.last_error?.error) ??
    "";

  // ✅ repo_summary gating for UI (tab + buttons)
  const repoSummaryAllowed = isTaskAllowedClientSide("repo_summary");

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16, maxWidth: 980, margin: "0 auto" }}>
      <header
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto",
          alignItems: "center",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>{t("app.title")}</h1>
          <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>
            <strong>Plan:</strong> {PLAN_TIER_LABELS[currentPlan] || currentPlan}
            {allowedError ? (
              <span style={{ marginLeft: 10, color: "#991B1B" }}>({allowedError})</span>
            ) : null}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
          <span style={{ opacity: 0.7, fontSize: 14 }}>
            {t("header.health")}: {health?.ok ? "OK" : "…"} {health?.app ? `(${health.app})` : ""}
          </span>
          <div style={{ fontSize: 12 }}>
            <span style={{ marginRight: 4 }}>{t("header.ui_language")}:</span>
            <select value={consoleLang} onChange={(e) => setConsoleLang(e.target.value)} style={{ fontSize: 12 }}>
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.label} ({opt.code})
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <TabButton active={tab === "queue"} onClick={() => setTab("queue")}>
            {t("tabs.queue")}
          </TabButton>
          <TabButton active={tab === "assistant"} onClick={() => setTab("assistant")}>
            {t("tabs.assistant")}
          </TabButton>
          <TabButton active={tab === "help"} onClick={() => setTab("help")}>
            {t("tabs.help")}
          </TabButton>
          <TabButton active={tab === "i18n"} onClick={() => setTab("i18n")}>
            {t("tabs.i18n")}
          </TabButton>
        </div>
      </div>

      {tab === "assistant" && (
        <div style={{ marginTop: 8 }}>
          <section
            style={{
              display: "grid",
              gap: 8,
              gridTemplateColumns: "1fr 1fr auto",
              alignItems: "end",
              marginBottom: 12,
            }}
          >
            <div>
              <label>API URL</label>
              <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="http://127.0.0.1:8010" />
            </div>
            <div>
              <label>API Key</label>
              <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </div>
            <div style={{ fontSize: 12, opacity: 0.7, paddingBottom: 8 }}>(saved locally)</div>
          </section>

          <AssistantPanel api={api} apiKey={apiKey} />
        </div>
      )}

      {tab === "help" && (
        <div style={{ marginTop: 8 }}>
          <HelpPanel />
        </div>
      )}

      {tab === "i18n" && (
        <div style={{ marginTop: 8 }}>
          <I18nPanel api={api} />
        </div>
      )}

      {tab === "queue" && (
        <>
          <section
            style={{
              display: "grid",
              gap: 8,
              gridTemplateColumns: "1fr 1fr auto",
              alignItems: "end",
              marginBottom: 12,
            }}
          >
            <div>
              <label>API URL</label>
              <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="http://127.0.0.1:8010" />
            </div>
            <div>
              <label>API Key</label>
              <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </div>
            <div style={{ fontSize: 12, opacity: 0.7, paddingBottom: 8 }}>(saved locally)</div>
          </section>

          <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
            <TabButton active={activeTab === "quick"} onClick={() => setActiveTab("quick")}>
              Quick Start
            </TabButton>
            <TabButton active={activeTab === "repo"} onClick={() => setActiveTab("repo")}>
              Repo insight
            </TabButton>
            <TabButton active={activeTab === "autodev"} onClick={() => setActiveTab("autodev")}>
              Autodev
            </TabButton>
          </div>

          {activeTab === "quick" && (
            <>
              <IntakeWizard onSubmit={submitIntake} busy={watching} />

              <section
                style={{
                  display: "grid",
                  gap: 12,
                  border: "1px solid #e5e7eb",
                  padding: 16,
                  borderRadius: 12,
                  marginTop: 16,
                  marginBottom: 16,
                }}
              >
                <h2 style={{ margin: 0 }}>Submit (manual)</h2>

                <label>Task</label>
                <select value={task} onChange={(e) => setTask(e.target.value)}>
                  {[
                    "plan",
                    "codegen",
                    "pipeline",
                    "intake",
                    // ✅ keep repo_summary visible but disabled when not supported
                    "repo_summary",
                    "packager",
                    "autodev",
                  ].map((tname) => {
                    const allowed = isTaskAllowedClientSide(tname);
                    return (
                      <option key={tname} value={tname} disabled={!allowed}>
                        {tname}
                        {!allowed ? " (not allowed)" : ""}
                      </option>
                    );
                  })}
                </select>

                <label>Idea</label>
                <input value={idea} onChange={(e) => setIdea(e.target.value)} />

                <label>Module</label>
                <input value={moduleName} onChange={(e) => setModuleName(e.target.value)} />

                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button onClick={submitTask} disabled={watching}>
                    {watching ? "Working…" : "Submit"}
                  </button>
                  <label style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto" }}>
                    <input type="checkbox" checked={rawMode} onChange={(e) => setRawMode(e.target.checked)} />
                    show raw JSON only
                  </label>
                </div>
              </section>
            </>
          )}

          {activeTab === "repo" && (
            <section style={{ border: "1px solid #e5e7eb", padding: 16, borderRadius: 12, marginBottom: 16 }}>
              <h2 style={{ marginTop: 0 }}>Repo insight (repo_summary)</h2>

              {!repoSummaryAllowed && (
                <div
                  style={{
                    marginBottom: 12,
                    padding: "10px 12px",
                    borderRadius: 8,
                    background: "#FFFBEB",
                    border: "1px solid #F59E0B",
                    color: "#92400E",
                    fontSize: 13,
                  }}
                >
                  <strong>repo_summary is not available</strong> on your backend (it does not appear in{" "}
                  <code>/tasks/allowed</code>).  
                  If you want this feature, you must add a worker handler named <code>repo_summary</code>, or remove this
                  tab from the console.
                </div>
              )}

              <label>Root</label>
              <input value={repoRoot} onChange={(e) => setRepoRoot(e.target.value)} placeholder="." />

              <div style={{ marginTop: 8, display: "flex", gap: 16, flexWrap: "wrap" }}>
                <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <input type="checkbox" checked={includeSnippets} onChange={(e) => setIncludeSnippets(e.target.checked)} />
                  include snippets (optional)
                </label>

                <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <input type="checkbox" checked={useFocusDirs} onChange={(e) => setUseFocusDirs(e.target.checked)} />
                  focus on selected dirs
                </label>
              </div>

              {useFocusDirs && (
                <div style={{ marginTop: 8 }}>
                  <label>Focus dirs (comma separated)</label>
                  <input value={focusDirs} onChange={(e) => setFocusDirs(e.target.value)} placeholder="src,services,agents,tests" />
                </div>
              )}

              <div style={{ marginTop: 12 }}>
                <button
                  onClick={() => {
                    setTask("repo_summary");
                    submitTask();
                  }}
                  disabled={watching || !repoSummaryAllowed}
                >
                  {watching ? "Running repo_summary…" : "Run repo_summary on repo"}
                </button>
              </div>
            </section>
          )}

          {activeTab === "autodev" && <AutodevPanel onRun={submitAutodev} busy={watching} />}

          <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
            <div style={{ border: "1px solid #e5e7eb", padding: 16, borderRadius: 12 }}>
              <h3 style={{ marginTop: 0 }}>Watch result</h3>

              <label>Job ID</label>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <input value={jobId} onChange={(e) => setJobId(e.target.value)} />
                <button onClick={poll} disabled={!jobId || watching}>
                  {watching ? "Watching…" : "Watch"}
                </button>
                {result?.status === "error" && (
                  <button onClick={retryLast} title="Re-enqueue the same task/payload">
                    Retry
                  </button>
                )}
              </div>

              {errorText && (
                <div
                  style={{
                    margin: "8px 0",
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: "#FEF2F2",
                    color: "#991B1B",
                    border: "1px solid #FCA5A5",
                    fontSize: 14,
                  }}
                >
                  <strong>Error:</strong> {String(errorText)}
                </div>
              )}

              {result && !rawMode && (
                <>
                  <div style={{ marginBottom: 8 }}>
                    <strong>Task:</strong> {result.task} &nbsp; <Badge status={result.status} />
                  </div>

                  <div style={{ marginBottom: 8 }}>
                    <strong>Payload:</strong>{" "}
                    <code style={{ background: "#e0f2fe", padding: "2px 6px", borderRadius: 6 }}>
                      {JSON.stringify(result.payload)}
                    </code>
                  </div>

                  <Subjobs result={result} />

                  {files.length > 0 && (
                    <div style={{ display: "grid", gap: 8, marginBottom: 8, marginTop: 8 }}>
                      <h4 style={{ margin: "8px 0" }}>Files</h4>
                      {files.map((f) => (
                        <FileCard key={f.path} f={f} />
                      ))}
                    </div>
                  )}

                  {/* repo_summary view stays here, but only meaningful if backend ever adds it */}
                  {result.task === "repo_summary" && <RepoSummaryView result={result} />}

                  {result.task === "packager" && result.result?.artifact_path && (
                    <div
                      style={{
                        marginTop: 8,
                        padding: "8px 12px",
                        borderRadius: 8,
                        background: "#ecfeff",
                        border: "1px solid #7dd3fc",
                        fontSize: 13,
                      }}
                    >
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>Packaged artifact</div>
                      <a
                        href={`${String(apiUrl).replace(/\/$/, "")}/artifacts/${
                          String(result.result.artifact_path).split("/").pop() || ""
                        }`}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          padding: "4px 10px",
                          borderRadius: 999,
                          background: "#0284c7",
                          color: "white",
                          textDecoration: "none",
                          fontSize: 12,
                        }}
                      >
                        Download ZIP
                      </a>
                    </div>
                  )}
                </>
              )}

              {result && (
                <pre
                  style={{
                    background: "#e0f2fe",
                    color: "#0f172a",
                    padding: 12,
                    borderRadius: 8,
                    maxHeight: 420,
                    overflow: "auto",
                    fontSize: 12,
                    marginTop: 8,
                  }}
                >
                  {pretty}
                </pre>
              )}
            </div>

            <div style={{ border: "1px solid #e5e7eb", padding: 16, borderRadius: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <h3 style={{ marginTop: 0, marginBottom: 0 }}>Recent</h3>
                <button
                  type="button"
                  onClick={() => refreshRecent()}
                  style={{
                    fontSize: 12,
                    padding: "6px 12px",
                    borderRadius: 999,
                    border: "none",
                    background: "#0284c7",
                    color: "white",
                    fontWeight: 600,
                    cursor: "pointer",
                    opacity: recentLoading ? 0.7 : 1,
                  }}
                  disabled={recentLoading}
                >
                  {recentLoading ? "Refreshing…" : "🔄 Refresh"}
                </button>
              </div>

              {recentError && (
                <div
                  style={{
                    marginBottom: 8,
                    padding: "6px 10px",
                    borderRadius: 8,
                    background: "#FEF2F2",
                    color: "#991B1B",
                    border: "1px solid #FCA5A5",
                    fontSize: 13,
                  }}
                >
                  <strong>Error loading recent:</strong> {recentError}
                </div>
              )}

              <div style={{ display: "grid", gap: 8, maxHeight: 320, overflowY: "auto", paddingRight: 4 }}>
                {recent.map((it) => {
                  const artifactName = it.artifact_name || (it.payload?.module ? `${it.payload.module}.zip` : null);

                  return (
                    <div
                      key={it.id}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "auto 1fr auto",
                        alignItems: "center",
                        gap: 8,
                        padding: 8,
                        border: "1px solid #eee",
                        borderRadius: 8,
                      }}
                    >
                      <code style={{ opacity: 0.7 }}>#{it.id}</code>
                      <div>
                        <div style={{ fontWeight: 600 }}>{it.task}</div>
                        <div style={{ fontSize: 12, opacity: 0.8, wordBreak: "break-all" }}>
                          {JSON.stringify(it.payload)}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Badge status={it.status} />
                        <button
                          onClick={() => {
                            setJobId(String(it.id));
                            setResult(null);
                            setWatching(true);
                            autoPoll(String(it.id));
                          }}
                        >
                          Watch
                        </button>
                        {it.task === "packager" && artifactName && (
                          <a
                            href={artifactsApi.url(artifactName)}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              fontSize: 11,
                              textDecoration: "none",
                              padding: "4px 8px",
                              borderRadius: 999,
                              border: "1px solid #0284c7",
                              color: "#0284c7",
                              background: "#f0f9ff",
                            }}
                          >
                            {artifactName}
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
                {recent.length === 0 && <div style={{ opacity: 0.7 }}>No recent items</div>}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
