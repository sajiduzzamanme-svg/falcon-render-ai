"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  createRender,
  getHealth,
  getRender,
  type InteriorStyle,
  type Mode,
  type Preset,
  type RenderDetail,
  type RoomType,
  type Style,
} from "@/lib/api";
import RenderJob from "../components/render-job";
import { useAuth } from "@/lib/auth";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_MIMES = ["image/png", "image/jpeg", "image/webp"];
const ACCEPTED_EXTS = ["png", "jpg", "jpeg", "webp"];
const ACCEPT_ATTR = ".png,.jpg,.jpeg,.webp";

const PRESETS: { value: Preset; label: string; swatch: string; hint: string }[] = [
  {
    value: "daylight",
    label: "Daylight",
    swatch: "linear-gradient(135deg,#7dd3fc 0%,#e0f2fe 60%,#fefce8 100%)",
    hint: "Bright natural light",
  },
  {
    value: "dusk",
    label: "Dusk",
    swatch: "linear-gradient(135deg,#312e81 0%,#c2410c 70%,#fbbf24 100%)",
    hint: "Golden hour, lights on",
  },
  {
    value: "night",
    label: "Night",
    swatch: "linear-gradient(135deg,#020617 0%,#1e3a8a 80%,#3b82f6 100%)",
    hint: "Artificial lighting",
  },
];

const STYLES: { value: Style; label: string; swatch: string; hint: string }[] = [
  {
    value: "modern",
    label: "Modern",
    swatch: "linear-gradient(135deg,#e2e8f0 0%,#94a3b8 100%)",
    hint: "Clean lines",
  },
  {
    value: "minimalist",
    label: "Minimalist",
    swatch: "linear-gradient(135deg,#ffffff 0%,#f1f5f9 100%)",
    hint: "White surfaces",
  },
  {
    value: "warm",
    label: "Warm",
    swatch: "linear-gradient(135deg,#fbbf24 0%,#b45309 100%)",
    hint: "Wood accents",
  },
];

const INTERIOR_STYLES: {
  value: InteriorStyle;
  label: string;
  swatch: string;
  hint: string;
}[] = [
  {
    value: "modern",
    label: "Modern",
    swatch: "linear-gradient(135deg,#e2e8f0 0%,#64748b 100%)",
    hint: "Clean lines, neutral tones",
  },
  {
    value: "scandinavian",
    label: "Scandinavian",
    swatch: "linear-gradient(135deg,#fef3c7 0%,#d6d3d1 100%)",
    hint: "Light wood, cozy hygge",
  },
  {
    value: "minimalist",
    label: "Minimalist",
    swatch: "linear-gradient(135deg,#ffffff 0%,#f1f5f9 100%)",
    hint: "Few pieces, calm space",
  },
  {
    value: "luxury",
    label: "Luxury",
    swatch: "linear-gradient(135deg,#fbbf24 0%,#78350f 100%)",
    hint: "Marble, brass, velvet",
  },
  {
    value: "traditional",
    label: "Traditional",
    swatch: "linear-gradient(135deg,#fdba74 0%,#9a3412 100%)",
    hint: "Classic wood, warm colors",
  },
];

const ROOM_TYPES: { value: RoomType; label: string }[] = [
  { value: "living", label: "Living room" },
  { value: "bedroom", label: "Bedroom" },
  { value: "kitchen", label: "Kitchen" },
  { value: "dining", label: "Dining" },
  { value: "office", label: "Office" },
];

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

function Dropzone({
  id,
  title,
  description,
  required,
  file,
  previewUrl,
  error,
  dragging,
  onPick,
  onDragState,
  inputRef,
}: {
  id: string;
  title: string;
  description: string;
  required: boolean;
  file: File | null;
  previewUrl: string | null;
  error: string | null;
  dragging: boolean;
  onPick: (f: File | null) => void;
  onDragState: (d: boolean) => void;
  inputRef: { current: HTMLInputElement | null };
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-slate-900">
          {title}{" "}
          <span
            className={`ml-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
              required
                ? "bg-blue-100 text-blue-800"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {required ? "Required" : "Optional"}
          </span>
        </h3>
      </div>
      <p className="mt-1 text-xs text-slate-500">{description}</p>
      <div
        role="button"
        tabIndex={0}
        aria-label={`${title}: drag and drop, or press Enter to browse`}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          onDragState(true);
        }}
        onDragLeave={() => onDragState(false)}
        onDrop={(e) => {
          e.preventDefault();
          onDragState(false);
          onPick(e.dataTransfer.files?.[0] ?? null);
        }}
        className={`mt-2 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
          dragging
            ? "border-blue-500 bg-blue-50"
            : "border-slate-300 bg-slate-50 hover:border-slate-400"
        }`}
      >
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={ACCEPT_ATTR}
          aria-label={title}
          className="sr-only"
          onChange={(e) => {
            onPick(e.target.files?.[0] ?? null);
            e.target.value = "";
          }}
        />
        {previewUrl && file ? (
          <img
            src={previewUrl}
            alt={`Preview of ${title}`}
            className="max-h-44 rounded-lg object-contain"
          />
        ) : (
          <>
            <p className="text-sm font-medium text-slate-700">
              Drop image here, or click to browse
            </p>
            <p className="mt-1 text-xs text-slate-500 tabular-nums">
              PNG, JPG, WebP — up to 10 MB
            </p>
          </>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm font-medium text-red-700">
          {error}
        </p>
      )}
      {file && !error && (
        <p className="mt-2 text-xs text-slate-600">
          <span className="font-medium">{file.name}</span>{" "}
          <span className="tabular-nums">
            ({(file.size / 1024 / 1024).toFixed(2)} MB)
          </span>{" "}
          <button
            type="button"
            onClick={() => onPick(null)}
            className="ml-1 font-medium text-blue-700 hover:underline"
          >
            Remove
          </button>
        </p>
      )}
    </div>
  );
}

export default function StudioPage() {
  const { session } = useAuth();
  const [health, setHealth] = useState<HealthState>("checking");
  const [sketch, setSketch] = useState<File | null>(null);
  const [sketchPreview, setSketchPreview] = useState<string | null>(null);
  const [sketchError, setSketchError] = useState<string | null>(null);
  const [sketchDrag, setSketchDrag] = useState(false);
  const [reference, setReference] = useState<File | null>(null);
  const [refPreview, setRefPreview] = useState<string | null>(null);
  const [refError, setRefError] = useState<string | null>(null);
  const [refDrag, setRefDrag] = useState(false);
  const [mode, setMode] = useState<Mode>("exterior");
  const [preset, setPreset] = useState<Preset>("daylight");
  const [style, setStyle] = useState<Style>("modern");
  const [interiorStyle, setInteriorStyle] = useState<InteriorStyle>("modern");
  const [roomType, setRoomType] = useState<RoomType>("living");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [job, setJob] = useState<RenderDetail | null>(null);
  const sketchInputRef = useRef<HTMLInputElement>(null);
  const refInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    return () => {
      if (sketchPreview) URL.revokeObjectURL(sketchPreview);
      if (refPreview) URL.revokeObjectURL(refPreview);
    };
  }, [sketchPreview, refPreview]);

  const pickSketch = useCallback(
    (candidate: File | null) => {
      if (sketchPreview) URL.revokeObjectURL(sketchPreview);
      setSketchPreview(null);
      setSketch(null);
      setSketchError(null);
      if (!candidate) return;
      const problem = validateFile(candidate);
      if (problem) {
        setSketchError(problem);
        return;
      }
      setSketch(candidate);
      setSketchPreview(URL.createObjectURL(candidate));
    },
    [sketchPreview],
  );

  const pickReference = useCallback(
    (candidate: File | null) => {
      if (refPreview) URL.revokeObjectURL(refPreview);
      setRefPreview(null);
      setReference(null);
      setRefError(null);
      if (!candidate) return;
      const problem = validateFile(candidate);
      if (problem) {
        setRefError(problem);
        return;
      }
      setReference(candidate);
      setRefPreview(URL.createObjectURL(candidate));
    },
    [refPreview],
  );

  const handleUpload = async () => {
    if (!sketch) return;
    setUploading(true);
    setUploadError(null);
    try {
      const token = session?.access_token;
      const created = await createRender(
        sketch,
        preset,
        mode === "interior" ? interiorStyle : style,
        reference,
        token,
        mode,
        mode === "interior" ? roomType : null,
      );
      const detail = await getRender(created.id, token);
      setJob(detail);
      // Scroll to the result once it renders.
      requestAnimationFrame(() => {
        document
          .getElementById("studio-result")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
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

  const canUpload = sketch !== null && !uploading && !sketchError;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Studio</h1>
          <p className="mt-1 text-slate-600">
            {mode === "interior"
              ? "Upload a blank room — get a fully furnished interior design. Room structure stays locked."
              : "Geometry-locked architectural renders — your design, never re-imagined."}
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

      {/* Mode toggle */}
      <div
        role="radiogroup"
        aria-label="What do you want to create?"
        className="grid grid-cols-2 gap-3"
      >
        {(
          [
            {
              value: "exterior",
              title: "Exterior Render",
              hint: "Sketch → photoreal building",
            },
            {
              value: "interior",
              title: "Interior Design",
              hint: "Blank room → furnished design",
            },
          ] as const
        ).map((m) => (
          <button
            key={m.value}
            type="button"
            role="radio"
            aria-checked={mode === m.value}
            onClick={() => setMode(m.value)}
            className={`rounded-2xl border-2 px-4 py-3 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              mode === m.value
                ? "border-blue-600 bg-blue-50 shadow-sm"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <span className="block text-sm font-bold text-slate-900 sm:text-base">
              {m.title}
            </span>
            <span className="mt-0.5 block text-xs text-slate-500">
              {m.hint}
            </span>
          </button>
        ))}
      </div>

      {/* Step 1 — uploads */}
      <section
        aria-label="Step 1: upload images"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h2 className="text-lg font-semibold">
          <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
            1
          </span>
          Upload
        </h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <Dropzone
            id="sketch-file"
            title={mode === "interior" ? "Your blank room photo" : "Your sketch"}
            description={
              mode === "interior"
                ? "A photo of the empty room. Walls, windows and viewpoint stay exactly as they are."
                : "3D model view, floor plan, or massing. Geometry always comes from here."
            }
            required
            file={sketch}
            previewUrl={sketchPreview}
            error={sketchError}
            dragging={sketchDrag}
            onPick={pickSketch}
            onDragState={setSketchDrag}
            inputRef={sketchInputRef}
          />
          <Dropzone
            id="reference-file"
            title="Style reference"
            description={
              mode === "interior"
                ? "A room you love — palette, materials, mood. Never its layout."
                : "Materials, colors, mood. Never geometry — your design stays locked."
            }
            required={false}
            file={reference}
            previewUrl={refPreview}
            error={refError}
            dragging={refDrag}
            onPick={pickReference}
            onDragState={setRefDrag}
            inputRef={refInputRef}
          />
        </div>
      </section>

      {/* Step 2 — look */}
      <section
        aria-label="Step 2: choose the look"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h2 className="text-lg font-semibold">
          <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
            2
          </span>
          Choose the look
        </h2>

        <fieldset className="mt-4">
          <legend className="text-sm font-semibold text-slate-900">
            Lighting
          </legend>
          <div
            role="radiogroup"
            aria-label="Lighting preset"
            className="mt-2 grid grid-cols-3 gap-3"
          >
            {PRESETS.map((p) => (
              <label
                key={p.value}
                className={`cursor-pointer overflow-hidden rounded-xl border-2 transition-all focus-within:ring-2 focus-within:ring-blue-500 ${
                  preset === p.value
                    ? "border-blue-600 shadow-md"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <input
                  type="radio"
                  name="preset"
                  value={p.value}
                  checked={preset === p.value}
                  onChange={() => setPreset(p.value)}
                  className="sr-only"
                />
                <div className="h-16 w-full" style={{ background: p.swatch }} />
                <div className="px-3 py-2">
                  <p className="text-sm font-semibold text-slate-900">
                    {p.label}
                  </p>
                  <p className="text-xs text-slate-500">{p.hint}</p>
                </div>
              </label>
            ))}
          </div>
        </fieldset>

        {mode === "interior" && (
          <fieldset className="mt-6">
            <legend className="text-sm font-semibold text-slate-900">
              Room type
            </legend>
            <div
              role="radiogroup"
              aria-label="Room type"
              className="mt-2 flex flex-wrap gap-2"
            >
              {ROOM_TYPES.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  role="radio"
                  aria-checked={roomType === r.value}
                  onClick={() => setRoomType(r.value)}
                  className={`rounded-full border-2 px-4 py-2 text-sm font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                    roomType === r.value
                      ? "border-blue-600 bg-blue-600 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <fieldset className="mt-6">
          <legend className="text-sm font-semibold text-slate-900">
            Design style
          </legend>
          <div
            role="radiogroup"
            aria-label="Design style"
            className="mt-2 grid grid-cols-3 gap-3"
          >
            {(mode === "interior" ? INTERIOR_STYLES : STYLES).map((s) => (
              <label
                key={s.value}
                className={`cursor-pointer overflow-hidden rounded-xl border-2 transition-all focus-within:ring-2 focus-within:ring-blue-500 ${
                  (mode === "interior" ? interiorStyle : style) === s.value
                    ? "border-blue-600 shadow-md"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <input
                  type="radio"
                  name="style"
                  value={s.value}
                  checked={
                    (mode === "interior" ? interiorStyle : style) === s.value
                  }
                  onChange={() =>
                    mode === "interior"
                      ? setInteriorStyle(s.value as InteriorStyle)
                      : setStyle(s.value as Style)
                  }
                  className="sr-only"
                />
                <div className="h-16 w-full" style={{ background: s.swatch }} />
                <div className="px-3 py-2">
                  <p className="text-sm font-semibold text-slate-900">
                    {s.label}
                  </p>
                  <p className="text-xs text-slate-500">{s.hint}</p>
                </div>
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      {/* Step 3 — generate */}
      <section
        aria-label="Step 3: generate"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h2 className="text-lg font-semibold">
          <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
            3
          </span>
          Generate
        </h2>
        {uploadError && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-900"
          >
            {uploadError}
          </div>
        )}
        <div className="mt-4">
          <button
            type="button"
            onClick={() => void handleUpload()}
            disabled={!canUpload}
            aria-disabled={!canUpload}
            title={!sketch ? "Choose your sketch first" : undefined}
            className="rounded-lg bg-blue-600 px-8 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
          >
            {uploading
              ? "Uploading…"
              : mode === "interior"
                ? "Generate interior design"
                : "Generate render"}
          </button>
          {!sketch && (
            <p className="mt-2 text-xs text-slate-500">
              {mode === "interior"
                ? "Choose your room photo above to activate."
                : "Choose your sketch above to activate."}
            </p>
          )}
        </div>
      </section>

      {job && (
        <div id="studio-result" aria-live="polite" className="scroll-mt-4">
          <RenderJob key={job.id} initial={job} />
        </div>
      )}
    </div>
  );
}
