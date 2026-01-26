import React, { useEffect, useState } from "react";

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

type Booking = {
  id: number;
  journey: Journey;
  passengers: number;
  total_price: number;
  currency: string;
  created_at: string;
};

export default function BookingsPage() {
  const [loading, setLoading] = useState(false);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadBookings() {
    setLoading(true);
    setError(null);

    try {
      let token: string | null = null;
      if (typeof window !== "undefined") {
        token = localStorage.getItem("velu_token");
      }

      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch("http://localhost:9002/v1/bookings", { headers });

      if (res.status === 401) {
        throw new Error("Not authorized. Please log in on the Login page first.");
      }

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data: Booking[] = await res.json();
      setBookings(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
      setBookings([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBookings();
  }, []);

  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4 flex justify-center">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-lg border border-slate-200 p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-baseline md:justify-between gap-2 mb-6">
          <div>
            <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500 mb-1">
              my_trips • bookings
            </p>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
              My bookings
            </h1>
            <p className="text-sm text-slate-600">
              A simple overview of journeys you have booked via the demo API.
            </p>
          </div>
          <a
            href="/"
            className="text-sm text-blue-600 hover:text-blue-700 hover:underline mt-2 md:mt-0"
          >
            ← Back to home
          </a>
        </div>

        <div className="flex items-center justify-between mb-4">
          <button
            type="button"
            onClick={loadBookings}
            disabled={loading}
            className="inline-flex justify-center items-center rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium px-4 py-2 h-[38px] shadow-sm transition"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
          <a
            href="/login"
            className="text-xs text-slate-500 hover:text-slate-700 hover:underline"
          >
            Need a token? Go to Login →
          </a>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {!error && !loading && bookings.length === 0 && (
          <p className="text-sm text-slate-500">
            No bookings yet. Make a booking from one of your journey cards (or from another
            demo page) and refresh.
          </p>
        )}

        {bookings.length > 0 && (
          <div className="space-y-3">
            {bookings.map((b) => (
              <div
                key={b.id}
                className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm flex flex-col gap-2"
              >
                <div className="flex items-baseline justify-between">
                  <h3 className="font-semibold text-slate-900">
                    {b.journey.title}
                  </h3>
                  <span className="text-xs text-slate-500">
                    #{b.id} • {new Date(b.created_at).toLocaleString()}
                  </span>
                </div>

                <p className="text-xs text-slate-500">
                  {b.journey.destination} · {b.journey.start_date} →{" "}
                  {b.journey.end_date}
                </p>

                <p className="text-sm text-slate-600 line-clamp-2">
                  {b.journey.description}
                </p>

                <div className="mt-2 flex items-center justify-between">
                  <div>
                    <div className="text-lg font-bold text-slate-900">
                      €{b.total_price.toFixed(0)}
                    </div>
                    <div className="text-xs text-slate-500">
                      {b.passengers} passenger{b.passengers !== 1 ? "s" : ""} ·{" "}
                      {b.currency}
                    </div>
                  </div>
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {b.journey.is_group ? "Group journey" : "Individual"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
