"use client";

import type { RenderStatus } from "@/lib/api";

const STYLES: Record<RenderStatus, string> = {
  queued: "bg-slate-100 text-slate-700 ring-slate-300",
  processing: "bg-blue-100 text-blue-800 ring-blue-300",
  succeeded: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  failed: "bg-red-100 text-red-800 ring-red-300",
};

export default function StatusBadge({ status }: { status: RenderStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ring-inset tabular-nums ${STYLES[status]}`}
      aria-label={`Status: ${status}`}
    >
      {status === "processing" && (
        <span
          className="mr-1.5 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-500"
          aria-hidden="true"
        />
      )}
      {status}
    </span>
  );
}
