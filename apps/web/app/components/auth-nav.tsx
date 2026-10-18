"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

const linkCls =
  "rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

/** Right side of the header nav: auth-aware links. */
export default function AuthNav() {
  const { configured, loading, user, signOut } = useAuth();

  return (
    <nav aria-label="Primary" className="flex items-center gap-1">
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
