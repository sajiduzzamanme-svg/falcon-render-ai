# Falcon Render AI

Geometry-fidelity architectural render platform. AI image tools "re-imagine"
instead of rendering — our edge is **design fidelity**: every render stays
locked to the input sketch's geometry (OpenCV Canny edge map extracted at
upload, passed to the provider alongside the sketch with a fidelity-focused
prompt).

Phase 1 render provider: Gemini image API (`gemini-2.5-flash-image`, Nano
Banana family). No `GEMINI_API_KEY` → HTTP 503
`RENDER_PROVIDER_NOT_CONFIGURED`. A missing provider is never presented as a
successful render.

## Backend

### Setup

```bash
cd apps/api
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Run

From `apps/api` (uses the project venv directly):

```bash
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Copy `.env.example` (repo root) to `.env` and set `GEMINI_API_KEY` to enable
live render generation. Never commit real keys.

### Env vars

| Var            | Default            | Notes                                      |
| -------------- | ------------------ | ------------------------------------------ |
| GEMINI_API_KEY | `""`               | Render provider key; empty → 503 on generate |
| API_HOST       | `127.0.0.1`        |                                            |
| API_PORT       | `8000`             |                                            |
| STORAGE_DIR    | `<repo>/storage`   | Jobs + artifacts (`sketch.png`, `edge.png`, `render.png`) |
| MAX_UPLOAD_MB  | `10`               | Upload size cap                            |

### API

| Method | Path                          | Description                                        |
| ------ | ----------------------------- | -------------------------------------------------- |
| GET    | `/api/v1/health`              | Health; `render_provider`: `gemini`/`unconfigured` |
| POST   | `/api/v1/renders`             | Multipart upload: `file` (png/jpg/jpeg/webp ≤10MB), `preset` (daylight\|dusk\|night), `style` (modern\|minimalist\|warm) → 201 |
| GET    | `/api/v1/renders`             | List jobs, newest first                            |
| GET    | `/api/v1/renders/{id}`        | Job detail incl. artifact URLs                     |
| POST   | `/api/v1/renders/{id}/generate` | Start generation (background thread) → 202; 503 without `GEMINI_API_KEY`; 409 if already processing/succeeded |
| GET    | `/api/v1/files/{id}/{kind}`   | `kind` = sketch\|edge\|render → image bytes; 404 `ARTIFACT_NOT_FOUND` when missing |

Errors always use the envelope `{"error": {"code": "...", "message": "..."}}`.

### Tests

```bash
cd apps/api
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check .
```

### Verify live generation (needs a real key)

```bash
export GEMINI_API_KEY=...   # never commit this

# 1. Upload a sketch
curl -s -X POST localhost:8000/api/v1/renders \
  -F "file=@sketch.png" -F "preset=dusk" -F "style=warm"
# → {"id":"<id>","status":"queued",...}

# 2. Start generation
curl -s -X POST localhost:8000/api/v1/renders/<id>/generate
# → {"id":"<id>","status":"processing"}   (202)

# 3. Poll until succeeded, then download
curl -s localhost:8000/api/v1/renders/<id> | grep '"status"'
curl -s -o render.png localhost:8000/api/v1/files/<id>/render
```

## Frontend

The Next.js 14 app lives in `apps/web/` (scaffolded by hand, no
create-next-app). It talks to the backend at
`process.env.NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

### Setup

```bash
cd apps/web
npm install
```

### Run (dev)

```bash
# default API base is http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Build

```bash
npm run build
npm start
```

Type checks: `npx tsc --noEmit`. Build: `npm run build`.

### Pages

- `/` — upload a sketch (drag-drop or click-to-browse, PNG/JPG/WebP ≤ 10 MB,
  validated client-side), pick a lighting preset (Daylight / Dusk / Night) and
  a style (Modern / Minimalist / Warm), then generate the render. Every job
  shows the sketch, the edge map labeled as the geometry lock, and the render
  with live 2 s polling. HTTP 503 from the provider surfaces an amber
  "set GEMINI_API_KEY on the API server and retry" banner; failures show the
  server message with a retry.
- `/renders` — gallery of all jobs (render thumbnail when succeeded, sketch
  thumbnail otherwise), with honest empty and error states.
- `/renders/[id]` — job detail: Sketch / Edge map (geometry lock) / Render
  panels, metadata, and a Generate button for queued or failed jobs.

## Docs

- `docs/decisions/0001-stack-and-scope.md` — stack + Phase 1 scope
