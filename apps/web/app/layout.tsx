import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Falcon Render AI",
  description: "Geometry-locked architectural renders — your design, preserved.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-100 font-sans text-slate-900 antialiased">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
            <Link
              href="/"
              className="text-lg font-bold tracking-tight text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Falcon Render AI
            </Link>
            <nav aria-label="Primary" className="flex gap-1">
              <Link
                href="/studio"
                className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                Studio
              </Link>
              <Link
                href="/renders"
                className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                Gallery
              </Link>
              <Link
                href="/pricing"
                className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                Pricing
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
            Renders are geometry-locked: every result is conditioned on the
            edge map extracted from your sketch.
          </div>
        </footer>
      </body>
    </html>
  );
}
