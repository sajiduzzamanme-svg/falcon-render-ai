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
