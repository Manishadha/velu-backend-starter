import React from "react";
import Link from "next/link";

export default function Navbar() {
  return (
    <header className="w-full border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-blue-600 text-xs font-semibold text-white">
            VT
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-slate-900">
              Velu Travel
            </p>
            <p className="text-[0.7rem] text-slate-500">
              Demo booking platform
            </p>
          </div>
        </div>

        <nav className="flex items-center gap-4 text-sm">
          <Link
            href="/"
            className="text-slate-600 hover:text-slate-900 hover:underline"
          >
            Overview
          </Link>
          <Link
            href="/search"
            className="text-slate-600 hover:text-slate-900 hover:underline"
          >
            Search trips
          </Link>
          <Link
            href="/bookings"
            className="text-slate-600 hover:text-slate-900 hover:underline"
          >
            My bookings
          </Link>
        </nav>
      </div>
    </header>
  );
}
