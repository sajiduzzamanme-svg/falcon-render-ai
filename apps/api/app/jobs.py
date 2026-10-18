"""Thread-safe JSON file job store.

Jobs live at STORAGE_DIR/{job_id}/job.json with artifacts beside them:
sketch.png, edge.png, render.png.
"""

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .config import settings
from .schemas import JobStatus

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _job_dir(job_id: str) -> Path:
    return Path(settings.STORAGE_DIR) / job_id


def _job_file(job_id: str) -> Path:
    return _job_dir(job_id) / "job.json"


def create(preset: str, style: str, user_id: str | None = None) -> dict:
    job_id = uuid.uuid4().hex
    record = {
        "id": job_id,
        "status": JobStatus.QUEUED.value,
        "preset": preset,
        "style": style,
        "user_id": user_id,
        "created_at": _now(),
        "updated_at": _now(),
        "error": None,
        "fidelity_score": None,
        "fidelity_attempts": 0,
    }
    with _lock:
        _job_dir(job_id).mkdir(parents=True, exist_ok=True)
        _job_file(job_id).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def get(job_id: str) -> dict | None:
    path = _job_file(job_id)
    if not path.exists():
        return None
    with _lock:
        return json.loads(path.read_text(encoding="utf-8"))


def list_jobs() -> list[dict]:
    base = Path(settings.STORAGE_DIR)
    jobs: list[dict] = []
    if not base.exists():
        return jobs
    with _lock:
        for child in base.iterdir():
            jf = child / "job.json"
            if jf.is_file():
                try:
                    jobs.append(json.loads(jf.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, OSError):
                    continue
    # Newest first.
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs


def update(job_id: str, **fields) -> dict | None:
    with _lock:
        path = _job_file(job_id)
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(fields)
        record["updated_at"] = _now()
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record


def artifact_path(job_id: str, kind: str) -> Path:
    return _job_dir(job_id) / f"{kind}.png"


def set_error(job_id: str, code: str, message: str) -> dict | None:
    return update(
        job_id,
        status=JobStatus.FAILED.value,
        error={"code": code, "message": message},
    )
