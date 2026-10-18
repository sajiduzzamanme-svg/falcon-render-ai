# 0001 — Stack and Phase 1 scope

Date: 2026-10-18

## Stack
- Backend: Python 3.12, FastAPI + Pydantic v2, httpx, OpenCV (headless, CPU) for geometry, pytest + ruff.
- Frontend: Next.js 14 (App Router), TypeScript strict, Tailwind CSS v3.
- Job store: JSON files under `./storage/{job_id}/job.json` — no database in Phase 1 (documented; Postgres later).
- No auth in Phase 1 (documented limitation; local dev only).

## Geometry-fidelity thesis
AI image tools "re-imagine" instead of rendering. Our edge: every render stays
locked to the input sketch's geometry. Phase 1 implements the verifiable part
of that lock: OpenCV Canny edge extraction on upload (stored as `edge.png`
evidence), plus a fidelity-focused prompt sent to the render provider together
with the sketch AND the edge map.

## Render provider
- Phase 1: Gemini image API (Nano Banana family, `gemini-2.5-flash-image`) via
  `GEMINI_API_KEY`. No key → HTTP 503 `RENDER_PROVIDER_NOT_CONFIGURED`.
  A missing provider is never presented as a successful render.
- Phase 2 (deferred — no GPU in this environment): ControlNet depth/normal
  conditioning for stronger geometric control. Do NOT attempt local diffusion.

## Out of scope for Phase 1
Auth, S3/object storage, background job queue (Redis/Celery), billing,
SketchUp/Blender adapters, LLM requirement extraction.
