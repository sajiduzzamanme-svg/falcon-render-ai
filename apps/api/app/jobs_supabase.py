"""Supabase-backed job store. Same interface as jobs.py (JSON file store).

DB column ``lighting`` maps to the app's ``preset`` field. The ``jobs``
table has no ``updated_at`` column, so reads report ``updated_at`` equal to
``created_at`` (documented limitation; a future migration can add it).

Artifacts (sketch/edge/render PNGs) stay on the local filesystem under
STORAGE_DIR with the same layout as the JSON store — Supabase Storage
migration is a separate step (ADR 0002).
"""

from __future__ import annotations

import json as _json
import uuid
from pathlib import Path

from .config import settings
from .schemas import JobStatus
from .supabase_client import SupabaseClient, SupabaseError, get_client

TABLE = "jobs"

# app field -> DB column
_FIELD_MAP = {
    "status": "status",
    "preset": "lighting",
    "style": "style",
    "user_id": "user_id",
    "sketch_path": "sketch_path",
    "edge_path": "edge_path",
    "reference_path": "reference_path",
    "render_path": "render_path",
    "fidelity_score": "fidelity_score",
    "fidelity_attempts": "fidelity_attempts",
    "credits_charged": "credits_charged",
}


def _resolve(client: SupabaseClient | None) -> SupabaseClient:
    resolved = client if client is not None else get_client()
    if resolved is None:
        raise SupabaseError("Supabase is not configured")
    return resolved


def _to_record(row: dict) -> dict:
    error = row.get("error")
    if isinstance(error, str) and error:
        try:
            error = _json.loads(error)
        except ValueError:
            error = {"code": "UNKNOWN", "message": error}
    elif not error:
        error = None
    created_at = row.get("created_at")
    score = row.get("fidelity_score")
    return {
        "id": row["id"],
        "user_id": row.get("user_id"),
        "status": row["status"],
        "preset": row.get("lighting"),
        "style": row.get("style"),
        "created_at": created_at,
        # No updated_at column in the jobs table (see module docstring).
        "updated_at": created_at,
        "error": error,
        "fidelity_score": float(score) if score is not None else None,
        "fidelity_attempts": row.get("fidelity_attempts", 0) or 0,
        "credits_charged": row.get("credits_charged", 0) or 0,
    }


def _to_row(fields: dict) -> dict:
    row: dict = {}
    for key, value in fields.items():
        if key == "error":
            row["error"] = _json.dumps(value) if isinstance(value, dict) else value
        elif key in _FIELD_MAP:
            row[_FIELD_MAP[key]] = value
        # else: app-only field with no DB column (e.g. updated_at) — dropped.
    return row


def create(
    preset: str,
    style: str,
    user_id: str | None = None,
    *,
    client: SupabaseClient | None = None,
) -> dict:
    c = _resolve(client)
    job_id = str(uuid.uuid4())
    # Keep the local artifact layout identical to the JSON store.
    artifact_path(job_id, "sketch").parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": job_id,
        "user_id": user_id,
        "status": JobStatus.QUEUED.value,
        "lighting": preset,
        "style": style,
        "sketch_path": f"{job_id}/sketch.png",
        "edge_path": f"{job_id}/edge.png",
    }
    rows = c.insert(TABLE, payload)
    if not rows:
        raise SupabaseError("Supabase insert returned no row")
    return _to_record(rows[0])


def get(job_id: str, *, client: SupabaseClient | None = None) -> dict | None:
    c = _resolve(client)
    rows = c.select(TABLE, params={"id": f"eq.{job_id}", "select": "*"})
    return _to_record(rows[0]) if rows else None


def list_jobs(*, client: SupabaseClient | None = None) -> list[dict]:
    c = _resolve(client)
    rows = c.select(TABLE, params={"select": "*", "order": "created_at.desc"})
    return [_to_record(r) for r in rows]


def update(
    job_id: str, *, client: SupabaseClient | None = None, **fields
) -> dict | None:
    c = _resolve(client)
    row = _to_row(fields)
    if not row:
        return get(job_id, client=c)
    rows = c.update(TABLE, row, params={"id": f"eq.{job_id}"})
    return _to_record(rows[0]) if rows else None


def set_error(
    job_id: str, code: str, message: str, *, client: SupabaseClient | None = None
) -> dict | None:
    return update(
        job_id,
        client=client,
        status=JobStatus.FAILED.value,
        error={"code": code, "message": message},
    )


def artifact_path(job_id: str, kind: str) -> Path:
    return Path(settings.STORAGE_DIR) / job_id / f"{kind}.png"
