"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { getSupabase, isSupabaseConfigured } from "@/lib/supabase";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "/studio";
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isSupabaseConfigured()) {
    return (
      <p className="text-sm text-slate-600">
        Sign-in is not configured yet (missing NEXT_PUBLIC_SUPABASE_URL /
        NEXT_PUBLIC_SUPABASE_ANON_KEY).
      </p>
    );
  }

  async function handleEmailAuth(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const supabase = getSupabase();
      const { error: authError } =
        mode === "signin"
          ? await supabase.auth.signInWithPassword({ email, password })
          : await supabase.auth.signUp({ email, password });
      if (authError) throw new Error(authError.message);
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleGoogle() {
    setBusy(true);
    setError(null);
    try {
      const { error: authError } = await getSupabase().auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}${next}` },
      });
      if (authError) throw new Error(authError.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed.");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-md space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {mode === "signin" ? "Sign in" : "Create your account"}
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          {mode === "signin"
            ? "Sign in to download full-resolution renders."
            : "One account for downloads, credits, and render history."}
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900"
        >
          {error}
        </div>
      )}

      <form onSubmit={(e) => void handleEmailAuth(e)} className="space-y-4">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Password</span>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Sign up"}
        </button>
      </form>

      <div className="relative text-center text-xs text-slate-500">
        <span className="bg-white px-2">or</span>
      </div>

      <button
        type="button"
        onClick={() => void handleGoogle()}
        disabled={busy}
        className="w-full rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
      >
        Continue with Google
      </button>

      <p className="text-center text-sm text-slate-600">
        {mode === "signin" ? "New here? " : "Already have an account? "}
        <button
          type="button"
          onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
          className="font-semibold text-blue-600 hover:underline"
        >
          {mode === "signin" ? "Create an account" : "Sign in"}
        </button>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="py-10">
      <Suspense fallback={<p className="text-sm text-slate-600">Loading…</p>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
