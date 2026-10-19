"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const linkCls =
  "rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

/** Right side of the header nav: auth-aware links + credit balance. */
export default function AuthNav({ mobile = false }: { mobile?: boolean }) {
  const { configured, loading, user, session, signOut } = useAuth();
  const [credits, setCredits] = useState<number | null>(null);

  // Credit balance for signed-in users (null in local-dev mode).
  useEffect(() => {
    let mounted = true;
    if (!configured || !user || !session) {
      setCredits(null);
      return;
    }
    getMe(session.access_token)
      .then((me) => {
        if (mounted) setCredits(me.credits);
      })
      .catch(() => {
        if (mounted) setCredits(null);
      });
    return () => {
      mounted = false;
    };
  }, [configured, user, session]);

  return (
    <nav
      aria-label="Primary"
      className={
        mobile
          ? "flex flex-col items-stretch gap-1"
          : "flex items-center gap-1"
      }
    >
      <Link href="/studio" className={linkCls}>
        Studio
      </Link>
      <Link href="/renders" className={linkCls}>
        Gallery
      </Link>
      <Link href="/pricing" className={linkCls}>
        Pricing
      </Link>
      {!configured || loading ? null : user ? (
        <>
          {credits !== null && (
            <span
              className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold tabular-nums text-amber-900"
              title="Your credit balance — 1 render = 10 credits"
            >
              {credits} credits
            </span>
          )}
          <span
            className="max-w-40 truncate px-2 text-sm text-slate-500"
            title={user.email ?? ""}
          >
            {user.email}
          </span>
          <button
            type="button"
            onClick={() => void signOut()}
            className={linkCls}
          >
            Sign out
          </button>
        </>
      ) : (
        <Link
          href="/login"
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          Sign in
        </Link>
      )}
    </nav>
  );
}
