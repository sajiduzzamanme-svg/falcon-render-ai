"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  fileUrl,
  generateRender,
  getRender,
  type RenderDetail,
} from "@/lib/api";
import StatusBadge from "./status-badge";

type Notice = { kind: "warn" | "error" | "info"; text: string } | null;

const NOTICE_STYLES: Record<NonNullable<Notice>["kind"], string> = {
  warn: "border-amber-300 bg-amber-50 text-amber-900",
  error: "border-red-300 bg-red-50 text-red-900",
  info: "border-blue-300 bg-blue-50 text-blue-900",
};

function formatDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

/**
 * Live panel for one render job: sketch, edge map (geometry lock), render,
 * metadata, generate button, polling, and honest 503 / failed handling.
 */
export default function RenderJob({ initial }: { initial: RenderDetail }) {
  const [detail, setDetail] = useState<RenderDetail>(initial);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const active =
    detail.status === "queued" || detail.status === "processing";

  // Poll while the job is active.
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(async () => {
      try {
        const next = await getRender(detail.id);
        setDetail(next);
      } catch (err) {
        if (err instanceof ApiError) {
          setNotice({
            kind: "error",
            text: `Lost contact with the API server: ${err.message}`,
          });
        } else {
          setNotice({
            kind: "error",
            text: "Lost contact with the API server.",
          });
        }
        clearInterval(timer);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [active, detail.id]);

  const handleGenerate = async () => {
    setBusy(true);
    setNotice(null);
    try {
      await generateRender(detail.id);
      setDetail(await getRender(detail.id));
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 503) {
          setNotice({
            kind: "warn",
            text: "Render provider not configured — set OPENROUTER_API_KEY or GEMINI_API_KEY on the API server and retry.",
          });
        } else if (err.status === 409) {
          setNotice({
            kind: "info",
            text: "A render is already running for this sketch — resuming.",
          });
          try {
            setDetail(await getRender(detail.id));
          } catch {
            // keep the current detail; the poll (or retry) will catch up
          }
        } else {
          setNotice({ kind: "error", text: err.message });
        }
      } else {
        setNotice({ kind: "error", text: "Could not reach the API server." });
      }
    } finally {
      setBusy(false);
    }
  };

  const showGenerate =
    (detail.status === "queued" || detail.status === "failed") && !busy;

  return (
    <section aria-label="Render job" className="space-y-4">
      {notice && (
        <div
          role="alert"
          className={`rounded-lg border px-4 py-3 text-sm font-medium ${NOTICE_STYLES[notice.kind]}`}
        >
          {notice.text}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <figure className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <img
            src={fileUrl(detail.artifacts.sketch)}
            alt="Uploaded architectural sketch"
            className="aspect-[4/3] w-full object-contain bg-slate-50"
          />
          <figcaption className="border-t border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Sketch
          </figcaption>
        </figure>

        <figure className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <img
            src={fileUrl(detail.artifacts.edge)}
            alt="Edge map extracted from the sketch — the geometry lock"
            className="aspect-[4/3] w-full object-contain bg-slate-50"
          />
          <figcaption className="border-t border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Geometry lock — edge map extracted from your sketch
          </figcaption>
        </figure>

        <figure className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          {detail.artifacts.render ? (
            <img
              src={fileUrl(detail.artifacts.render)}
              alt="Geometry-locked architectural render"
              className="aspect-[4/3] w-full object-contain bg-slate-50"
            />
          ) : (
            <div
              className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 bg-slate-50 px-4 text-center"
              role="status"
            >
              {detail.status === "failed" ? (
                <p className="text-sm font-medium text-red-700">
                  Render failed. The server reported:
                  <br />
                  <span className="font-normal">
                    {detail.error?.message ?? "Unknown error."}
                  </span>
                </p>
              ) : detail.status === "processing" ? (
                <>
                  <span
                    className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
                    aria-hidden="true"
                  />
                  <p className="text-sm font-medium text-slate-600">
                    Rendering — your geometry lock is being preserved.
                  </p>
                </>
              ) : (
                <p className="text-sm font-medium text-slate-600">
                  No render yet. Generate one to see the result here.
                </p>
              )}
            </div>
          )}
          <figcaption className="border-t border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Render
          </figcaption>
        </figure>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
        <StatusBadge status={detail.status} />
        <span className="text-slate-600">
          Preset: <strong className="font-semibold capitalize text-slate-900">{detail.preset}</strong>
        </span>
        <span className="text-slate-600">
          Style: <strong className="font-semibold capitalize text-slate-900">{detail.style}</strong>
        </span>
        {detail.fidelity_score !== null && detail.fidelity_score !== undefined && (
          <span className="text-slate-600">
            Fidelity:{" "}
            <strong
              className={`font-semibold tabular-nums ${
                detail.fidelity_score >= 0.55 ? "text-emerald-700" : "text-amber-700"
              }`}
              title="Edge-recall vs the sketch geometry lock — higher means the design survived rendering"
            >
              {Math.round(detail.fidelity_score * 100)}%
            </strong>{" "}
            <span className="text-slate-400">
              ({detail.fidelity_attempts} attempt{detail.fidelity_attempts === 1 ? "" : "s"})
            </span>
          </span>
        )}
        <span className="text-slate-600">
          Created: <time className="tabular-nums text-slate-900">{formatDate(detail.created_at)}</time>
        </span>
        <span className="text-slate-600">
          Updated: <time className="tabular-nums text-slate-900">{formatDate(detail.updated_at)}</time>
        </span>
      </div>

      {showGenerate && (
        <button
          type="button"
          onClick={handleGenerate}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Generate render
        </button>
      )}
      {busy && (
        <p className="text-sm text-slate-600" role="status">
          Starting render…
        </p>
      )}
    </section>
  );
}
