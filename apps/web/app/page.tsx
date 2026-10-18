"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  createRender,
  getHealth,
  getRender,
  type Preset,
  type RenderDetail,
  type Style,
} from "@/lib/api";
import RenderJob from "./components/render-job";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_MIMES = ["image/png", "image/jpeg", "image/webp"];
const ACCEPTED_EXTS = ["png", "jpg", "jpeg", "webp"];
const ACCEPT_ATTR = ".png,.jpg,.jpeg,.webp";

const PRESETS: Preset[] = ["daylight", "dusk", "night"];
const STYLES: Style[] = ["modern", "minimalist", "warm"];

function validateFile(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const typeOk =
    ACCEPTED_MIMES.includes(file.type) || ACCEPTED_EXTS.includes(ext);
  if (!typeOk) {
    return "Only PNG, JPG, or WebP images are accepted.";
  }
  if (file.size > MAX_BYTES) {
    return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 10 MB.`;
  }
  return null;
}

type HealthState = "checking" | "ok" | "down";

export default function HomePage() {
  const [health, setHealth] = useState<HealthState>("checking");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [preset, setPreset] = useState<Preset>("daylight");
  const [style, setStyle] = useState<Style>("modern");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [job, setJob] = useState<RenderDetail | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const checkHealth = useCallback(async () => {
    setHealth("checking");
    try {
      await getHealth();
      setHealth("ok");
    } catch {
      setHealth("down");
    }
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  // Revoke the preview object URL when it is replaced or on unmount.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const pickFile = useCallback(
    (candidate: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setFile(null);
      setFileError(null);
      if (!candidate) return;
      const problem = validateFile(candidate);
      if (problem) {
        setFileError(problem);
        return;
      }
      setFile(candidate);
      setPreviewUrl(URL.createObjectURL(candidate));
    },
    [previewUrl],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files?.[0] ?? null;
      pickFile(dropped);
    },
    [pickFile],
  );

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const created = await createRender(file, preset, style);
      const detail = await getRender(created.id);
      setJob(detail);
    } catch (err) {
      if (err instanceof ApiError) {
        setUploadError(err.message);
      } else {
        setUploadError("Could not reach the API server.");
      }
    } finally {
      setUploading(false);
    }
  };

  const canUpload = file !== null && !uploading;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Falcon Render AI
          </h1>
          <p className="mt-1 text-slate-600">
            Geometry-locked architectural renders
          </p>
        </div>
        <div aria-live="polite">
          {health === "ok" && (
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-800 ring-1 ring-inset ring-emerald-300">
              <span
                className="h-2 w-2 rounded-full bg-emerald-500"
                aria-hidden="true"
              />
              API connected
            </span>
          )}
          {health === "down" && (
            <span className="inline-flex items-center gap-2 rounded-full bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 ring-1 ring-inset ring-red-300">
              <span
                className="h-2 w-2 rounded-full bg-red-500"
                aria-hidden="true"
              />
              API unreachable — start the backend
              <button
                type="button"
                onClick={() => void checkHealth()}
                className="ml-1 rounded-md bg-red-600 px-2 py-0.5 text-xs font-semibold text-white hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
              >
                Retry
              </button>
            </span>
          )}
          {health === "checking" && (
            <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-inset ring-slate-300">
              Checking API…
            </span>
          )}
        </div>
      </div>

      <section
        aria-label="Upload a sketch"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h2 className="text-lg font-semibold">Upload a sketch</h2>
        <p className="mt-1 text-sm text-slate-600">
          Drop an architectural sketch or photo. We extract its edge map as a
          geometry lock before rendering, so your design is never re-imagined.
        </p>

        <div
          role="button"
          tabIndex={0}
          aria-label="Choose a sketch file: drag and drop, or press Enter to browse"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
            dragging
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 bg-slate-50 hover:border-slate-400"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            aria-label="Sketch file"
            className="sr-only"
            onChange={(e) => {
              pickFile(e.target.files?.[0] ?? null);
              e.target.value = "";
            }}
          />
          {previewUrl && file ? (
            <img
              src={previewUrl}
              alt="Preview of the selected sketch"
              className="max-h-56 rounded-lg object-contain"
            />
          ) : (
            <>
              <p className="text-sm font-medium text-slate-700">
                Drag and drop your sketch here, or click to browse
              </p>
              <p className="mt-1 text-xs text-slate-500 tabular-nums">
                PNG, JPG, or WebP — up to 10 MB
              </p>
            </>
          )}
        </div>

        {fileError && (
          <p role="alert" className="mt-2 text-sm font-medium text-red-700">
            {fileError}
          </p>
        )}
        {file && !fileError && (
          <p className="mt-2 text-sm text-slate-600">
            Selected: <span className="font-medium">{file.name}</span>{" "}
            <span className="tabular-nums">
              ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </span>
          </p>
        )}

        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          <fieldset>
            <legend className="text-sm font-semibold text-slate-900">
              Lighting preset
            </legend>
            <div
              role="radiogroup"
              aria-label="Lighting preset"
              className="mt-2 inline-flex rounded-lg border border-slate-300 bg-slate-50 p-1"
            >
              {PRESETS.map((p) => (
                <label
                  key={p}
                  className={`cursor-pointer rounded-md px-4 py-2 text-sm font-medium capitalize transition-colors focus-within:ring-2 focus-within:ring-blue-500 ${
                    preset === p
                      ? "bg-white text-blue-700 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <input
                    type="radio"
                    name="preset"
                    value={p}
                    checked={preset === p}
                    onChange={() => setPreset(p)}
                    className="sr-only"
                  />
                  {p}
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor="style-select"
              className="text-sm font-semibold text-slate-900"
            >
              Design style
            </label>
            <select
              id="style-select"
              value={style}
              onChange={(e) => setStyle(e.target.value as Style)}
              className="mt-2 block w-full max-w-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              {STYLES.map((s) => (
                <option key={s} value={s} className="capitalize">
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {uploadError && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-900"
          >
            {uploadError}
          </div>
        )}

        <div className="mt-6">
          <button
            type="button"
            onClick={() => void handleUpload()}
            disabled={!canUpload}
            aria-disabled={!canUpload}
            title={!file ? "Choose a valid sketch file first" : undefined}
            className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
          {!file && (
            <p className="mt-2 text-xs text-slate-500">
              The Upload button activates once a valid file is chosen.
            </p>
          )}
        </div>
      </section>

      {job && (
        <div aria-live="polite">
          <RenderJob key={job.id} initial={job} />
        </div>
      )}
    </div>
  );
}
