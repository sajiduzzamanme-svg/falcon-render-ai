"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, getRender, type RenderDetail } from "@/lib/api";
import RenderJob from "../../components/render-job";

export default function RenderDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const [detail, setDetail] = useState<RenderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setDetail(await getRender(id));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 404
            ? "Render not found. It may have been deleted."
            : err.message,
        );
      } else {
        setError("Could not reach the API server.");
      }
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/renders"
          className="text-sm font-medium text-blue-600 hover:text-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          ← Back to gallery
        </Link>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Render detail
        </h1>
      </div>

      {!detail && !error && (
        <p className="text-slate-600" role="status">
          Loading render…
        </p>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-900"
        >
          <p>{error}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-2 rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
          >
            Retry
          </button>
        </div>
      )}

      {detail && (
        <div aria-live="polite">
          <RenderJob key={detail.id} initial={detail} />
        </div>
      )}
    </div>
  );
}
