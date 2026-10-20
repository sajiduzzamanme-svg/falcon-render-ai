"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, fileUrl, listRenders, type RenderItem } from "@/lib/api";
import StatusBadge from "../components/status-badge";

function formatDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function thumbnailFor(item: RenderItem): { src: string; fallback: string; alt: string } {
  const sketch = fileUrl(`/api/v1/files/${encodeURIComponent(item.id)}/sketch`);
  if (item.status === "succeeded") {
    return {
      // Watermarked preview is public; the full-resolution file is gated.
      src: fileUrl(`/api/v1/files/${encodeURIComponent(item.id)}/preview`),
      fallback: sketch,
      alt: `Render of job ${item.id}`,
    };
  }
  return {
    src: sketch,
    fallback: sketch,
    alt: `Sketch for job ${item.id} (render not available yet)`,
  };
}

export default function GalleryPage() {
  const [items, setItems] = useState<RenderItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await listRenders();
      setItems(res.items);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Could not reach the API server.");
      }
      setItems([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Gallery</h1>
        <p className="mt-1 text-slate-600">
          Every render is locked to the edge map of its sketch.
        </p>
      </div>

      {items === null && !error && (
        <p className="text-slate-600" role="status">
          Loading renders…
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

      {items !== null && !error && items.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
          <p className="text-lg font-semibold text-slate-900">No renders yet</p>
          <p className="mt-1 text-sm text-slate-600">
            Upload a sketch to create your first geometry-locked render.
          </p>
          <Link
            href="/"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Upload a sketch
          </Link>
        </div>
      )}

      {items !== null && items.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const thumb = thumbnailFor(item);
            return (
              <Link
                key={item.id}
                href={`/renders/${encodeURIComponent(item.id)}`}
                className="group overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <img
                  src={thumb.src}
                  alt={thumb.alt}
                  className="aspect-[4/3] w-full object-cover bg-slate-50"
                  loading="lazy"
                  onError={(e) => {
                    // Older jobs predate watermarked previews — fall back.
                    const el = e.currentTarget;
                    if (el.src !== thumb.fallback) el.src = thumb.fallback;
                  }}
                />
                <div className="space-y-2 border-t border-slate-100 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={item.status} />
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                        item.mode === "interior"
                          ? "bg-violet-100 text-violet-800 ring-violet-300"
                          : "bg-sky-100 text-sky-800 ring-sky-300"
                      }`}
                    >
                      {item.mode === "interior"
                        ? `Interior${item.room_type ? ` · ${item.room_type}` : ""}`
                        : "Exterior"}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600">
                    <span className="font-medium capitalize text-slate-900">
                      {item.preset}
                    </span>{" "}
                    ·{" "}
                    <span className="font-medium capitalize text-slate-900">
                      {item.style}
                    </span>
                  </p>
                  <p className="text-xs text-slate-500 tabular-nums">
                    Created {formatDate(item.created_at)}
                    {item.fidelity_score !== null && item.fidelity_score !== undefined && (
                      <> · Fidelity {Math.round(item.fidelity_score * 100)}%</>
                    )}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
