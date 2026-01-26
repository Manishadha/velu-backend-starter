import React, { useState } from "react";

type LoginResponse = {
  access_token: string;
  token_type: string;
  account_id: string;
  user_id: string;
};

export default function LoginPage() {
  const [email, setEmail] = useState("mani@example.com");
  const [password, setPassword] = useState("secret");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [response, setResponse] = useState<LoginResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    try {
      const res = await fetch("http://localhost:9002/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        throw new Error(`Login failed: ${res.status}`);
      }

      const data: LoginResponse = await res.json();
      setResponse(data);

      if (typeof window !== "undefined") {
        localStorage.setItem("velu_token", data.access_token);
        localStorage.setItem("velu_account_id", data.account_id);
        localStorage.setItem("velu_user_id", data.user_id);
      }

      setInfo("Login successful. Token stored in browser. You can now open the Journeys page.");
    } catch (err: any) {
      setError(err.message || "Unknown error");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4 flex justify-center">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg border border-slate-200 p-6">
        <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500 mb-2">
          my_trips • login
        </p>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Sign in</h1>
        <p className="text-sm text-slate-600 mb-4">
          Demo login that calls your FastAPI auth endpoint and stores the token for API calls.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3 mb-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Email
            </label>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Password
            </label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex justify-center items-center rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium px-4 py-2 h-[40px] shadow-sm transition"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {error && (
          <div className="mb-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {info && (
          <div className="mb-3 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-700">
            {info}
          </div>
        )}

        {response && (
          <div className="mt-3 rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-xs text-slate-700 space-y-1">
            <div>
              <span className="font-mono">access_token:</span>{" "}
              <span className="break-all">{response.access_token}</span>
            </div>
            <div>
              <span className="font-mono">account_id:</span> {response.account_id}
            </div>
            <div>
              <span className="font-mono">user_id:</span> {response.user_id}
            </div>
          </div>
        )}

        <a
          href="/journeys"
          className="mt-4 inline-block text-xs text-blue-600 hover:text-blue-700 hover:underline"
        >
          → Go to Journeys (after login)
        </a>
      </div>
    </main>
  );
}
