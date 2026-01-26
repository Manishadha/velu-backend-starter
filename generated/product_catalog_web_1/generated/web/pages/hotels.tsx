"use client";

import React, { useState } from "react";

type Hotel = {
  id: number;
  city: string;
  name: string;
  check_in: string;
  check_out: string;
  price_per_night_eur: number;
  stars: number;
  free_cancellation: boolean;
};

export default function HotelsPage() {
  const [city, setCity] = useState("Lisbon");
  const [checkIn, setCheckIn] = useState("2025-12-02");
  const [checkOut, setCheckOut] = useState("2025-12-09");
  const [minStars, setMinStars] = useState(3);
  const [freeCancelOnly, setFreeCancelOnly] = useState(false);
  const [sortBy, setSortBy] = useState<"price" | "stars">("price");

  const [results, setResults] = useState<Hotel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      city,
      check_in: checkIn,
      check_out: checkOut,
      min_stars: String(minStars),
      free_cancel_only: freeCancelOnly ? "true" : "false",
      sort_by: sortBy,
    });

    try {
      const res = await fetch(`http://127.0.0.1:9001/hotels/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }
      const data: Hotel[] = await res.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message || "Failed to search hotels");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4 flex justify-center">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-xl border border-slate-200 p-8 space-y-8">
        <header>
          <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500 mb-2">
            travel_app_v11 • hotels
          </p>
          <h1 className="text-2xl font-bold mb-2">Search hotels</h1>
          <p className="text-sm text-slate-600">
            Try Lisbon with the default dates to see the sample results.
          </p>
        </header>

        <form onSubmit={handleSearch} className="grid gap-4 md:grid-cols-4 items-end">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">City</label>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Check-in</label>
            <input
              type="date"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={checkIn}
              onChange={(e) => setCheckIn(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Check-out</label>
            <input
              type="date"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={checkOut}
              onChange={(e) => setCheckOut(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Min stars</label>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={minStars}
              onChange={(e) => setMinStars(Number(e.target.value))}
            >
              <option value={1}>1+</option>
              <option value={2}>2+</option>
              <option value={3}>3+</option>
              <option value={4}>4+</option>
              <option value={5}>5</option>
            </select>
          </div>

          <div className="flex items-center gap-2 col-span-2">
            <input
              id="freecancel"
              type="checkbox"
              className="rounded border-slate-300"
              checked={freeCancelOnly}
              onChange={(e) => setFreeCancelOnly(e.target.checked)}
            />
            <label htmlFor="freecancel" className="text-xs text-slate-700">
              Free cancellation only
            </label>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Sort by</label>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "price" | "stars")}
            >
              <option value="price">Price</option>
              <option value="stars">Stars</option>
            </select>
          </div>

          <button
            type="submit"
            className="inline-flex justify-center rounded-lg bg-blue-600 text-white text-sm font-medium px-4 py-2 hover:bg-blue-700 disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "Searching..." : "Search hotels"}
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
            <p className="text-sm text-slate-500">No hotels yet. Run a search.</p>
          )}

          <div className="space-y-3">
            {results.map((h) => (
              <div
                key={h.id}
                className="border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
              >
                <div>
                  <p className="text-sm font-semibold">{h.name}</p>
                  <p className="text-xs text-slate-500">
                    {h.city} • {h.check_in} → {h.check_out}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {"★".repeat(h.stars)}{" "}
                    {h.free_cancellation ? "• Free cancellation" : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold">
                    €{h.price_per_night_eur.toFixed(0)} <span className="text-xs font-normal">/ night</span>
                  </p>
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
