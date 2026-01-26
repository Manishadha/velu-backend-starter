import { useEffect, useState } from "react";
import "./index.css";

const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8203";

const FALLBACK_LOCALES = ["en", "fr", "nl", "de", "ar", "ta"];

export default function App() {
  const [locales, setLocales] = useState(FALLBACK_LOCALES);
  const [currentLocale, setCurrentLocale] = useState("en");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadLocales() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/v1/i18n/locales`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled && Array.isArray(data.locales) && data.locales.length) {
          setLocales(data.locales);
          if (!data.locales.includes(currentLocale)) {
            setCurrentLocale(data.locales[0]);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError("Failed to load locales, using defaults.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadLocales();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>React multi-language demo</h1>
        <p className="app-subtitle">
          Frontend reads supported languages from
          <code className="code-pill">
            {API_BASE}/v1/i18n/locales
          </code>
          .
        </p>
      </header>

      <main className="app-main">
        <section className="card">
          <label className="label">Locale</label>
          <div className="row">
            <select
              value={currentLocale}
              onChange={(e) => setCurrentLocale(e.target.value)}
              disabled={loading}
            >
              {locales.map((loc) => (
                <option key={loc} value={loc}>
                  {loc}
                </option>
              ))}
            </select>
            {loading && <span className="hint">Loading…</span>}
          </div>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="card">
          <h2>Current language</h2>
          <p>
            Selected language code:
            <span className="pill">{currentLocale}</span>
          </p>
        </section>

        <section className="card">
          <h2>All supported languages</h2>
          <p className="hint">
            List comes from the API when reachable, otherwise from defaults
            bundled in the SPA.
          </p>
          <div className="pill-row">
            {locales.map((loc) => (
              <span key={loc} className="pill">
                {loc}
              </span>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
