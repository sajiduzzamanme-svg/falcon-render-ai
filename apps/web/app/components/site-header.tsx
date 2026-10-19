"use client";

import Link from "next/link";
import { useState } from "react";
import AuthNav from "./auth-nav";

/**
 * Site header: full nav on desktop, hamburger menu on mobile.
 */
export default function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link
          href="/"
          className="text-lg font-bold tracking-tight text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          onClick={() => setOpen(false)}
        >
          Falcon Render AI
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:block">
          <AuthNav />
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 md:hidden"
          aria-expanded={open}
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <path d="M5 5l12 12M17 5L5 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <path d="M3 6h16M3 11h16M3 16h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile menu panel */}
      {open && (
        <nav
          aria-label="Mobile"
          className="border-t border-slate-200 bg-white px-4 py-3 md:hidden"
        >
          <div onClick={() => setOpen(false)}>
            <AuthNav mobile />
          </div>
        </nav>
      )}
    </header>
  );
}
