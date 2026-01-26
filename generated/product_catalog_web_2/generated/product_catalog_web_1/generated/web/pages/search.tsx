import React, { useState } from "react";
import Navbar from "../components/Navbar";

type Trip = {
  id: number;
  kind: "flight" | "hotel";
  origin: string;
  destination: string;
  depart_date: string;
  return_date: string | null;
  title: string;
  description: string;
  price: number;
  currency: string;
  airline: string | null;
  hotel_name: string | null;
  rating: number | null;
};

export default function SearchPage() {
  const [origin, setOrigin] = useState("BRU");
  const [destination, setDestination] = useState("JFK");
  const [travelDate, setTravelDate] = useState("2025-12-20");
  const [kind, setKind] = useState<"flight" | "hotel" | "">("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Trip[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [bookingStatus, setBookingStatus] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setBookingStatus(null);

    const params = new URLSearchParams();
    if (origin) params.append("origin", origin);
    if (destination) params.append("destination", destination);
    if (travelDate) params.append("travel_date", travelDate);
    if (kind) params.append("kind", kind);

    try {
      const res = await fetch(
        `http://localhost:9001/search/trips?${params.toString()}`
      );
      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }
      const data: Trip[] = await res.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />

      <main className="py-10 px-4 flex justify-center">
        <div className="w-full max-w-5xl bg-white rounded-2xl shadow-lg border border-slate-200 p-6 md:p-8">
          <div className="flex flex-col md:flex-row md:items-baseline md:justify-between gap-2 mb-6">
            <div>
              <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500 mb-1">
                travel_app_v11 • search
              </p>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
                Find your next trip ✈️🏨
              </h1>
              <p className="text-sm text-slate-600">
                Search our demo dataset of flights and hotels powered by a
                FastAPI backend.
              </p>
            </div>
          </div>

          {/* Search form */}
          <form
            onSubmit={handleSearch}
            className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-6 items-end"
          >
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Origin
              </label>
              <input
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="BRU"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Destination
              </label>
              <input
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="JFK"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Date
              </label>
              <input
                type="date"
                value={travelDate}
                onChange={(e) => setTravelDate(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Type
              </label>
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value as any)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Flights &amp; Hotels</option>
                <option value="flight">Flights only</option>
                <option value="hotel">Hotels only</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex justify-center items-center rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium px-4 py-2 h-[38px] md:h-[42px] shadow-sm transition"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </form>

          {/* Error / booking status */}
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {bookingStatus && !error && (
            <div className="mb-4 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-700">
              {bookingStatus}
            </div>
          )}

          {!error && !loading && results.length === 0 && (
            <p className="text-sm text-slate-500">
              No results yet. Try a search using the form above.
            </p>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div className="space-y-3">
              {results.map((trip) => (
                <div
                  key={trip.id}
                  className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm flex flex-col gap-2"
                >
                  <div className="flex items-baseline justify-between">
                    <h3 className="font-semibold text-slate-900">
                      {trip.title}
                    </h3>
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {trip.kind === "flight" ? "Flight" : "Hotel"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500">
                    {trip.origin} → {trip.destination} · {trip.depart_date}
                  </p>

                  <p className="text-sm text-slate-600 line-clamp-2">
                    {trip.description}
                  </p>

                  <div className="mt-2 flex items-center justify-between">
                    <div>
                      <div className="text-lg font-bold text-slate-900">
                        €
                        {trip.price.toFixed(0)}{" "}
                        <span className="text-xs font-normal text-slate-500">
                          {trip.currency}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        per traveller
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          setBookingStatus("Booking trip…");
                          const res = await fetch("http://localhost:9001/bookings", {
                            method: "POST",
                            headers: {
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                              trip_id: trip.id,
                              customer_name: "Demo User",
                              email: "demo@example.com",
                              passengers: 1,
                            }),
                          });

                          if (!res.ok) {
                            throw new Error(`Booking failed: ${res.status}`);
                          }

                          const data = await res.json();
                          setBookingStatus(
                            `Booking confirmed! Reference #${data.id} – total €${data.total_price}`
                          );
                        } catch (err) {
                          console.error(err);
                          setBookingStatus(
                            "Booking failed. Please try again."
                          );
                        }
                      }}
                      className="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                    >
                      Book this trip
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
