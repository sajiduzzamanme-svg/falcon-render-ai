import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import SiteHeader from "./components/site-header";
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
        <AuthProvider>
          <SiteHeader />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        </AuthProvider>
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
