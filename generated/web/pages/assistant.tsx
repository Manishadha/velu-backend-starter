import React, { useState } from "react";
import type { NextPage } from "next";

type AssistantResponse = {
  ok: boolean;
  language: string;
  intake?: any;
  blueprint?: any;
  i18n?: {
    locales?: string[];
    messages?: Record<string, unknown>;
    summary?: Record<string, unknown>;
  };
};

const AssistantPage: NextPage = () => {
  const [companyName, setCompanyName] = useState("Acme Travel");
  const [idea, setIdea] = useState("tableau de bord pour mon équipe en français");
  const [localesInput, setLocalesInput] = useState("en,fr");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AssistantResponse | null>(null);

  const handleSubmit = async (evt: React.FormEvent) => {
    evt.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const rawLocales = localesInput
        .split(",")
        .map((x) => x.trim())
        .filter((x) => x.length > 0);

      const product: any = {
        type: "saas",
        goal: "internal_tool",
      };
      if (rawLocales.length > 0) {
        product.locales = rawLocales;
      }

      const body = {
        company: { name: companyName || "My Company" },
        product,
        idea: idea || "dashboard for my team",
      };

      const res = await fetch("http://localhost:8000/v1/assistant/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        setError("Request failed with status " + res.status);
        setResult(null);
        return;
      }

      const data = (await res.json()) as AssistantResponse;
      setResult(data);
    } catch (e) {
      setError("Failed to call assistant endpoint");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const detectedLanguage = result?.language || "";
  const i18n = result?.i18n || {};
  const i18nLocales: string[] = Array.isArray(i18n.locales)
    ? (i18n.locales as string[])
    : [];
  const i18nMessages: Record<string, unknown> =
    (i18n.messages as Record<string, unknown>) || {};

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4 flex justify-center">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-xl border border-slate-200 p-8 space-y-8">
        <header className="space-y-1">
          <p className="text-[0.7rem] uppercase tracking-[0.25em] text-slate-500">
            velu • assistant intake demo
          </p>
          <h1 className="text-2xl font-bold text-slate-900">
            From idea to blueprint + i18n
          </h1>
          <p className="text-sm text-slate-600">
            This page calls the assistant intake endpoint and shows the detected
            language, product locales, and generated i18n content.
          </p>
        </header>

        <section className="grid gap-8 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1.7fr)] items-start">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-800">
                Company name
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-800">
                App idea
              </label>
              <textarea
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                rows={4}
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 resize-y"
              />
              <p className="text-[0.7rem] text-slate-500">
                You can write in any language. The backend will try to detect it.
              </p>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-800">
                Product locales (optional, comma separated)
              </label>
              <input
                type="text"
                value={localesInput}
                onChange={(e) => setLocalesInput(e.target.value)}
                className="w-full border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
              />
              <p className="text-[0.7rem] text-slate-500">
                Example: en,fr or de,ar. If left empty, the assistant can infer based on the idea.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-4 py-2 rounded-md text-sm font-semibold bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-60"
            >
              {loading ? "Thinking…" : "Run assistant intake"}
            </button>

            {error && (
              <p className="text-xs text-red-600 mt-1">
                {error}
              </p>
            )}
          </form>

          <div className="space-y-4">
            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-600 space-y-1">
              <p className="font-semibold text-slate-800 text-sm">
                Current result
              </p>
              <p>
                Detected language:{" "}
                <span className="font-mono text-[0.75rem]">
                  {detectedLanguage || "—"}
                </span>
              </p>
              <p>
                i18n locales:{" "}
                <span className="font-mono text-[0.75rem]">
                  {i18nLocales.length > 0 ? i18nLocales.join(", ") : "—"}
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-700 space-y-3 max-h-[420px] overflow-auto">
              {!result && !loading && (
                <p className="text-slate-500 text-sm">
                  Submit the form to see the assistant intake output.
                </p>
              )}

              {loading && (
                <p className="text-slate-500 text-sm">
                  Waiting for assistant response…
                </p>
              )}

              {!loading &&
                result &&
                i18nLocales.map((code) => (
                  <div key={code} className="space-y-1">
                    <p className="font-semibold text-slate-900 text-xs">
                      Locale {code}
                    </p>
                    <pre className="whitespace-pre-wrap break-words text-[0.7rem] bg-white border border-slate-200 rounded-md px-3 py-2">
                      {JSON.stringify(i18nMessages[code] ?? {}, null, 2)}
                    </pre>
                  </div>
                ))}
            </div>
          </div>
        </section>

        <section className="border border-dashed border-slate-300 rounded-xl p-4 text-xs text-slate-600 space-y-1">
          <p>
            Backend endpoint:{" "}
            <span className="font-mono text-[0.75rem]">
              POST /v1/assistant/intake
            </span>
          </p>
          <p>
            This page is a thin wrapper around that endpoint, useful as a manual
            smoke test for language detection, intake, blueprint localization, and
            i18n content generation.
          </p>
        </section>
      </div>
    </main>
  );
};

export default AssistantPage;
