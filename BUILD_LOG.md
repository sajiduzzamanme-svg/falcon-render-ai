# Falcon Render AI — BUILD_LOG

## 2026-10-18 — Phase 1 kickoff
- Repo scaffolded at `~/workspace/falcon-render-ai`, git init on `main`.
- Env: Python 3.12.3 venv (`apps/api/.venv`), Node v24.20.0.
- Backend deps installed: fastapi, uvicorn[standard], pydantic v2,
  pydantic-settings, python-multipart, httpx, opencv-python-headless 5.0.0,
  numpy, pillow, pytest, ruff. Verified: `import cv2` OK.
- Plan: backend + frontend built in parallel by two workers against a fixed
  API contract (see coordinator brief); coordinator re-runs full suite before
  reporting.

## 2026-10-18 — Phase 1 backend complete
- Built FastAPI backend in `apps/api/app/`: `main.py` (CORS localhost:3000, error envelope, no tracebacks), `config.py` (pydantic-settings; GEMINI_API_KEY="", STORAGE_DIR=<repo>/storage, MAX_UPLOAD_MB=10), `schemas.py` (JobStatus enum, all shapes), `jobs.py` (thread-safe JSON job store at STORAGE_DIR/{id}/job.json + sketch/edge/render.png artifacts), `geometry.py` (Canny 100/200 after GaussianBlur(5,5); raises GeometryError).
- Adapters: `adapters/base.py` (RenderAdapter ABC, ProviderNotConfigured, RenderFailed); `adapters/gemini.py` (REST gemini-2.5-flash-image:generateContent, x-goog-api-key header, fidelity prompt: preserve exact geometry/massing/proportions/window-door placement/viewpoint + preset lighting + style, 120s timeout; 503 path when key missing).
- Routes implement exact contract: GET /api/v1/health; POST /api/v1/renders (validates size ≤10MB, extension, PIL magic bytes; 201 queued); GET /api/v1/renders (newest first); GET /api/v1/renders/{id}; POST /api/v1/renders/{id}/generate (202, daemon thread; 503 RENDER_PROVIDER_NOT_CONFIGURED; 409 JOB_ALREADY_RUNNING/SUCCEEDED); GET /api/v1/files/{id}/{kind} (404 ARTIFACT_NOT_FOUND).
- Tests: 17 passed (`apps/api/.venv/bin/python -m pytest apps/api/tests -q`): geometry (synthetic 400x300 fixture: edge exists, non-empty, same W/H, edge pixels >0; unreadable→GeometryError) + API (health, upload 201, txt/oversize/bad preset/bad style → 422 with exact codes, 503 without key, 404s, artifact download, 409 guards).
- ruff: clean (`ruff check apps/api` → All checks passed; format clean).
- Live smoke test on uvicorn :8123: health/upload/detail/edge download/render-404/generate-503/bad-upload-422/list all matched contract; smoke job cleaned from storage/.
- `apps/api/requirements.txt` pinned; README.md Backend section added (setup, run, env, API table, live-generation curl).
- NOT VERIFIED: actual Gemini live generation (no GEMINI_API_KEY available); the 202→background-thread→adapter→render.png path is exercised only via 503/409/404 guards. needs real key + curl POST localhost:8000/api/v1/renders/{id}/generate to verify.

## 2026-10-18 — Phase 1 frontend (apps/web)
- Hand-scaffolded Next.js 14.2.35 + React 18.3.1 + TypeScript (strict) +
  Tailwind 3.4.19 in `apps/web/` (no create-next-app).
- Files: `package.json`, `tsconfig.json` (strict: true), `next.config.mjs`,
  `tailwind.config.ts` (content: ./app/**), `postcss.config.mjs`,
  `app/layout.tsx`, `app/globals.css`, `lib/api.ts` (typed client + ApiError
  {status, code, message}, fileUrl), `app/components/status-badge.tsx`,
  `app/components/render-job.tsx` (shared job panel: sketch / edge-map
  geometry-lock / render panels, generate button, 2s polling, 503 + failed
  handling), `app/page.tsx` (health badge, drag-drop + click upload,
  client-side type/size ≤10MB validation, preset segmented control, style
  select, job card), `app/renders/page.tsx` (gallery grid, honest empty/error
  states), `app/renders/[id]/page.tsx` (detail with generate for queued/failed).
- `npx tsc --noEmit` → exit 0, no errors.
- `npm run build` → exit 0: "✓ Compiled successfully", 5 static/dynamic
  routes, type checking passed.
- README.md: added Frontend section (setup / dev with NEXT_PUBLIC_API_URL /
  build / pages). No .env files committed (only repo-root .env.example).

## 2026-10-18 — Coordinator personal verification (Phase 1)
Re-ran everything the workers built; did not trust their reports alone.

Backend (commit 874f5f0):
- `pytest apps/api/tests -q` → **17 passed** (3 geometry + 14 API), re-run by coordinator.
- `ruff check` + `ruff format --check` → clean.
- Live E2E vs real uvicorn server (zero mocks): health 200 (`render_provider: unconfigured`); PNG upload → 201 queued; detail shows sketch/edge URLs + render:null; edge download 200 image/png with dims identical to input (400×300) and 2492 edge pixels (real Canny output); render-before-generation → 404; generate without key → **503 RENDER_PROVIDER_NOT_CONFIGURED** (honest, no fake image); bad extension → 422 INVALID_UPLOAD; bad preset → 422; unknown job → 404. Test job removed from storage/ afterwards.

Frontend (commit e7f9885):
- `npx tsc --noEmit` → clean. `npm run build` → success, routes: /, /renders, /renders/[id], /_not-found.
- Full-stack smoke: `next start` + uvicorn together → / → 200 ("Falcon Render AI"), /renders → 200, /renders/abc123 → 200, backend health ok.

Regressions fixed during verification: none (workers' code passed as-is).
Test artifacts cleaned; storage/ empty; no secrets committed (secret scan: clean).

## 2026-10-18 — OpenRouter adapter live-verified
- Added `app/adapters/openrouter.py` (Nano Banana via OpenRouter chat completions, sketch+edge as image inputs, fidelity prompt); provider auto-selection prefers OpenRouter, falls back to direct Gemini.
- Fixed env-specific httpx crash (NO_PROXY `*[::1]` entries break env-proxy mount parsing) via `app/adapters/http.py`: trust_env=False + explicit proxy + system CA bundle (egress TLS interception).
- Live E2E with real key (transient, never stored): health 200 (provider=openrouter) → upload 201 → generate 202 → succeeded; 1.3MB render downloaded and visually confirmed geometry-faithful to the input massing.
- Tests: 20/20 pass, ruff clean.

## 2026-10-18 — Fidelity scorer (geometry drift detector)
- New `app/fidelity.py`: edge-recall score (0.0–1.0) of each render against the
  sketch edge map (tolerance 3px). Recall, not precision — renders legitimately
  add edges (foliage/texture); what matters is sketch edges surviving.
- Calibrated on real renders: faithful (edge-conditioned) ~0.66, roof-drifted
  ~0.45. Suggested FIDELITY_MIN_SCORE start: 0.55 (default 0.0 = gate off,
  score still recorded — no surprise provider spend).
- `_run_generation` retries up to FIDELITY_MAX_ATTEMPTS while score < gate;
  best attempt always kept; score + attempts stored on job, exposed via API.
- UI: fidelity badge on job detail + gallery; 503 notice mentions both keys.
- Tests: 27/27 pass (6 new fidelity unit tests incl. identical/blank/shifted/
  resized/unreadable cases, retry-until-max-attempts, score in job detail);
  ruff clean; tsc clean; `npm run build` OK.

## 2026-10-18 — Studio v0.2 UI rebuild
- Reference image upload (optional): validated like sketch, stored as
  reference.png, served via /files/{id}/reference, shown as 4th panel.
  Adapters send it as a third, style-only image (materials/colors/mood —
  never geometry) with updated fidelity prompt.
- Studio home rebuilt: numbered steps, dual dropzones (sketch required /
  reference optional) with clear geometry-vs-style copy, visual preset cards
  (gradient swatches) for lighting + style, Generate CTA.
- RenderJob: reference panel, sketch-vs-render CompareSlider (drag +
  keyboard), Download button (beta: direct; note that signup gate ships
  with Supabase Auth), fidelity badge already present.
- Tests: 30/30 pass (3 new reference-upload tests); ruff clean; tsc clean;
  `npm run build` OK. Screenshots verified via local Playwright.

## 2026-10-18 — Supabase backend wiring (ADR 0002)
- New `apps/api/app/supabase_client.py`: minimal PostgREST client over httpx.
  Secret server key travels in the `apikey` header (verified working pattern
  for `sb_secret_...` keys; the legacy `service_role` JWT does NOT bypass
  RLS via `apikey` alone — verified against the live project). Key is read
  from env only (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`), never logged.
  Reuses `adapters/http.py` `http_client` (trust_env=False + explicit proxy)
  to avoid the known httpx env-proxy crash.
- New `apps/api/app/jobs_supabase.py`: Supabase-backed job store with the
  same interface as `jobs.py` (`create/get/list_jobs/update/set_error/
  artifact_path`). Field mapping: app `preset` <-> DB `lighting`; `error`
  dict <-> JSON TEXT; `updated_at` reported as `created_at` (the `jobs`
  table has no `updated_at` column — future migration candidate). Artifacts
  stay on local disk under STORAGE_DIR (Supabase Storage is a later step).
- New `apps/api/app/job_store.py`: backend selection proxy. Supabase is used
  when both env vars are set, else the JSON file store (local-dev fallback).
  Resolves per access, so tests can switch via monkeypatched settings.
  Routes changed one line: `from .. import jobs` -> `from ..job_store import
  jobs`; all call sites untouched.
- New `apps/api/app/credits.py` (ADR 0003): `CREDITS_PER_RENDER = 10`.
  `ensure_can_generate` runs at generate time (402 INSUFFICIENT_CREDITS /
  403 FREE_TRIAL_EXHAUSTED); `settle_job` deducts 10 on success (ledger
  reason='render', profiles.credits, jobs.credits_charged), consumes the
  anonymous free trial (`anonymous_trials` by SHA256 IP hash) on success.
  Failed renders never touch credits. SPEC TENSION: the wiring brief said
  "deduct 10 per render ATTEMPT (fidelity retry loop!)"; implemented per
  ADR 0003 instead — one charge per completed render, fidelity retries free
  — since ADR 0003 is the accepted pricing decision. One-function change in
  `settle_job` if per-attempt billing is wanted.
- Routes: `POST /renders/{id}/generate` takes `request: Request` for the
  client hash; `_run_generation` accepts `user_id`/`client_hash` kwargs and
  settles credits after a successful render (settlement failures are logged
  server-side and never fail the render — known gap: no transactional
  outbox yet). Auth (signup-gated download) is intentionally NOT
  implemented — separate next step; `user_id` plumbing is ready.
- `config.py`: added `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` ("" = JSON mode).
- Tests: `apps/api/tests/test_supabase_store.py` — 15 new tests: store
  selection, proxy delegation, CRUD round-trip, lighting/preset mapping,
  error serialization, list ordering, charge math (100 -> 90, ledger
  -10/'render', credits_charged=10), failed-never-charged, insufficient
  credits, anonymous trial flow (incl. failed render not burning trial),
  JSON-fallback no-ops, plus 2 LIVE tests (CRUD + trial) against the real
  project via the connector surrogate (skipped without credential; every
  live row cleaned up). Existing `test_api.py` fixture now forces JSON mode
  so the suite is hermetic.
- Results: **45/45 pass** (30 pre-existing + 15 new), ruff check + format
  clean. Live verification via `bin/sb-rest`: tables exist and are empty
  after the test run.
- NOT VERIFIED: end-to-end render with live provider key (no render key in
  this env — the generate->settle path is unit-tested, not live-fired).
