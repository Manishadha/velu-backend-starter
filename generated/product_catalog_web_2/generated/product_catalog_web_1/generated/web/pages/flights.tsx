"use client";

import React, { useState } from "react";

type Flight = {
  id: number;
  from_city: string;
  to_city: string;
  depart_date: string;
  return_date?: string | null;
  airline: string;
  price_eur: number;
  duration_hours: number;
  nonstop: boolean;
};

export default function FlightsPage() {
  const [fromCity, setFromCity] = useState("Brussels");
  const [toCity, setToCity] = useState("Lisbon");
  const [departDate, setDepartDate] = useState("2025-12-02");
  const [returnDate, setReturnDate] = useState("2025-12-09");
  const [nonstopOnly, setNonstopOnly] = useState(false);
  const [sortBy, setSortBy] = useState<"price" | "duration">("price");

  const [results, setResults] = useState<Flight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      from_city: fromCity,
      to_city: toCity,
      depart_date: departDate,
      return_date: returnDate,
      nonstop_only: nonstopOnly ? "true" : "false",
      sort_by: sortBy,
    });

    try {
      const res = await fetch(`http://127.0.0.1:9001/flights/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }
      const data: Flight[] = await res.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message || "Failed to search flights");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4 flex justify-center">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-xl border border-slate-200 p-8 space-y-8">
        <header>
          <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500 mb-2">
            travel_app_v11 • flights
          </p>
          <h1 className="text-2xl font-bold mb-2">Search flights</h1>
          <p className="text-sm text-slate-600">
            Try Brussels → Lisbon with the default dates to see the sample results.
          </p>
        </header>

        <form onSubmit={handleSearch} className="grid gap-4 md:grid-cols-4 items-end">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">From</label>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={fromCity}
              onChange={(e) => setFromCity(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">To</label>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={toCity}
              onChange={(e) => setToCity(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Depart</label>
            <input
              type="date"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={departDate}
              onChange={(e) => setDepartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Return</label>
            <input
              type="date"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={returnDate}
              onChange={(e) => setReturnDate(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2 col-span-2">
            <input
              id="nonstop"
              type="checkbox"
              className="rounded border-slate-300"
              checked={nonstopOnly}
              onChange={(e) => setNonstopOnly(e.target.checked)}
            />
            <label htmlFor="nonstop" className="text-xs text-slate-700">
              Nonstop only
            </label>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Sort by</label>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "price" | "duration")}
            >
              <option value="price">Price</option>
              <option value="duration">Duration</option>
            </select>
          </div>

          <button
            type="submit"
            className="inline-flex justify-center rounded-lg bg-blue-600 text-white text-sm font-medium px-4 py-2 hover:bg-blue-700 disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "Searching..." : "Search flights"}
          </button>
        </form>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Results</h2>
          {results.length === 0 && !loading && (
            <p className="text-sm text-slate-500">No flights yet. Run a search.</p>
          )}

          <div className="space-y-3">
            {results.map((f) => (
              <div
                key={f.id}
                className="border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
              >
                <div>
                  <p className="text-sm font-semibold">
                    {f.from_city} → {f.to_city}
                  </p>
                  <p className="text-xs text-slate-500">
                    {f.depart_date}
                    {f.return_date ? ` • return ${f.return_date}` : ""}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {f.airline} • {f.duration_hours.toFixed(1)}h •{" "}
                    {f.nonstop ? "Nonstop" : "1+ stops"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold">€{f.price_eur.toFixed(0)}</p>
                  <button className="mt-1 text-xs rounded-lg border border-blue-600 text-blue-600 px-3 py-1 hover:bg-blue-50">
                    Select
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
