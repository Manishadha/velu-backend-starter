import React, { useState, useEffect } from "react";

type Journey = {
  id: number;
  destination: string;
  title: string;
  description: string;
  start_date: string;
  end_date: string;
  is_group: boolean;
  max_people: number;
  price_per_person: number;
  currency: string;
};

export default function JourneysPage() {
  const [destination, setDestination] = useState("");
  const [groupOnly, setGroupOnly] = useState(false);
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function fetchJourneys() {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    if (destination.trim()) params.append("destination", destination.trim());
    if (groupOnly) params.append("group_only", "true");
    if (maxPrice.trim()) params.append("max_price", maxPrice.trim());

    try {
      let token: string | null = null;
      if (typeof window !== "undefined") {
        token = localStorage.getItem("velu_token");
      }

      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(
        `http://localhost:9002/v1/journeys?${params.toString()}`,
        { headers }
      );

      if (res.status === 401) {
        throw new Error("Not authorized. Please log in on the Login page first.");
      }

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data: Journey[] = await res.json();
      setJourneys(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
      setJourneys([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchJourneys();
  }, []);

  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4 flex justify-center">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-lg border border-slate-200 p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-baseline md:justify-between gap-2 mb-6">
          <div>
            <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500 mb-1">
              my_trips • journeys
            </p>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
              Explore journeys 🌍
            </h1>
            <p className="text-sm text-slate-600">
              Filter trips by destination, price, and group journeys powered by your new
              My Trips API.
            </p>
          </div>
          <a
            href="/"
            className="text-sm text-blue-600 hover:text-blue-700 hover:underline mt-2 md:mt-0"
          >
            ← Back to home
          </a>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            fetchJourneys();
          }}
          className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6 items-end"
        >
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Destination
            </label>
            <input
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Paris, New York..."
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Max price (EUR)
            </label>
            <input
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g. 1000"
            />
          </div>

          <label className="inline-flex items-center text-xs font-medium text-slate-600 gap-2">
            <input
              type="checkbox"
              checked={groupOnly}
              onChange={(e) => setGroupOnly(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            Show only group journeys
          </label>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex justify-center items-center rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium px-4 py-2 h-[38px] md:h-[42px] shadow-sm transition"
          >
            {loading ? "Filtering..." : "Filter"}
          </button>
        </form>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {!error && !loading && journeys.length === 0 && (
          <p className="text-sm text-slate-500">
            No journeys found for this filter. Try clearing filters or changing
            destination/price.
          </p>
        )}

        {journeys.length > 0 && (
          <div className="space-y-3">
            {journeys.map((j) => (
              <div
                key={j.id}
                className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm flex flex-col gap-2"
              >
                <div className="flex items-baseline justify-between">
                  <h3 className="font-semibold text-slate-900">{j.title}</h3>
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {j.is_group ? "Group journey" : "Individual"}
                  </span>
                </div>

                <p className="text-xs text-slate-500">
                  {j.destination} · {j.start_date} → {j.end_date}
                </p>

                <p className="text-sm text-slate-600 line-clamp-2">
                  {j.description}
                </p>

                <div className="mt-2 flex items-center justify-between">
                  <div>
                    <div className="text-lg font-bold text-slate-900">
                      €{j.price_per_person.toFixed(0)}
                    </div>
                    <div className="text-xs text-slate-500">
                      per person · max {j.max_people} people
                    </div>
                  </div>
                  <a
                    href="/bookings"
                    className="text-xs text-blue-600 hover:text-blue-700 hover:underline"
                  >
                    View my bookings →
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
