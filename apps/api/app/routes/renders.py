"""Render job endpoints."""

import io
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from .. import jobs
from ..adapters.base import ProviderNotConfigured, RenderAdapter, RenderFailed
from ..adapters.gemini import GeminiRenderAdapter
from ..adapters.openrouter import OpenRouterRenderAdapter
from ..config import settings
from ..fidelity import FidelityError, fidelity_score
from ..geometry import GeometryError, extract_edges
from ..schemas import (
    PRESETS,
    STYLES,
    JobStatus,
    RenderJobResponse,
    RenderListResponse,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
FILE_KINDS = {"sketch", "edge", "render"}


def error_response(http_status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message}},
    )


def job_not_found(job_id: str) -> JSONResponse:
    return error_response(
        status.HTTP_404_NOT_FOUND, "JOB_NOT_FOUND", f"No render job with id '{job_id}'."
    )


def _job_to_summary(record: dict) -> dict:
    return {
        "id": record["id"],
        "status": record["status"],
        "preset": record["preset"],
        "style": record["style"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "fidelity_score": record.get("fidelity_score"),
    }


def _job_to_detail(record: dict) -> dict:
    job_id = record["id"]
    detail = _job_to_summary(record)
    detail["fidelity_attempts"] = record.get("fidelity_attempts", 0)
    detail["error"] = record.get("error")
    detail["artifacts"] = {
        "sketch": f"/api/v1/files/{job_id}/sketch",
        "edge": f"/api/v1/files/{job_id}/edge",
        "render": f"/api/v1/files/{job_id}/render"
        if jobs.artifact_path(job_id, "render").exists()
        else None,
    }
    return detail


def _validate_image(
    content: bytes, filename: str | None
) -> tuple[bytes, str] | JSONResponse:
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_UPLOAD",
            f"File exceeds {settings.MAX_UPLOAD_MB}MB.",
        )
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_UPLOAD",
            "File must be png, jpg, jpeg, or webp.",
        )
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
        with Image.open(io.BytesIO(content)) as img:
            fmt = img.format
        if fmt not in ALLOWED_FORMATS:
            raise ValueError(fmt)
    except (OSError, ValueError):
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_UPLOAD",
            "File is not a readable image.",
        )
    return (content, ext)


@router.post("/renders", status_code=status.HTTP_201_CREATED)
async def create_render(
    file: UploadFile = File(...),  # noqa: B008 — standard FastAPI dependency idiom
    preset: str = Form(...),
    style: str = Form(...),
) -> JSONResponse:
    if preset not in PRESETS:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_PRESET",
            f"preset must be one of: {', '.join(PRESETS)}.",
        )
    if style not in STYLES:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_STYLE",
            f"style must be one of: {', '.join(STYLES)}.",
        )

    content = await file.read()
    validated = _validate_image(content, file.filename)
    if isinstance(validated, JSONResponse):
        return validated

    record = jobs.create(preset=preset, style=style)
    job_id = record["id"]
    try:
        sketch_path = jobs.artifact_path(job_id, "sketch")
        sketch_path.write_bytes(content)
        edge_path = jobs.artifact_path(job_id, "edge")
        extract_edges(sketch_path, edge_path)
    except GeometryError as exc:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_UPLOAD", str(exc)
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "id": job_id,
            "status": JobStatus.QUEUED.value,
            "preset": preset,
            "style": style,
            "created_at": record["created_at"],
        },
    )


@router.get("/renders", response_model=RenderListResponse)
def list_renders() -> dict:
    records = jobs.list_jobs()
    return {
        "items": [_job_to_summary(r) for r in records],
        "total": len(records),
    }


@router.get("/renders/{job_id}", response_model=RenderJobResponse)
def get_render(job_id: str):
    record = jobs.get(job_id)
    if record is None:
        return job_not_found(job_id)
    return _job_to_detail(record)


def _select_adapter() -> RenderAdapter | None:
    """Prefer OpenRouter when its key is set, else direct Gemini. None = unconfigured."""
    if OpenRouterRenderAdapter(
        settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL
    ).configured:
        return OpenRouterRenderAdapter(
            settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL
        )
    if GeminiRenderAdapter(settings.GEMINI_API_KEY).configured:
        return GeminiRenderAdapter(settings.GEMINI_API_KEY)
    return None


def _run_generation(job_id: str) -> None:
    record = jobs.get(job_id)
    if record is None:
        return
    adapter = _select_adapter()
    if adapter is None:  # key removed between accept and run — fail honestly
        jobs.set_error(
            job_id, "RENDER_FAILED", "Render provider is no longer configured."
        )
        return
    sketch_path = jobs.artifact_path(job_id, "sketch")
    edge_path = jobs.artifact_path(job_id, "edge")
    best_score = 0.0
    best_bytes: bytes | None = None
    attempts = 0
    try:
        max_attempts = max(1, settings.FIDELITY_MAX_ATTEMPTS)
        for _ in range(max_attempts):
            attempts += 1
            image_bytes = adapter.generate(
                sketch_path,
                edge_path,
                record["preset"],
                record["style"],
            )
            try:
                score = fidelity_score(edge_path, image_bytes)
            except FidelityError:
                score = 0.0
            if best_bytes is None or score > best_score:
                best_score, best_bytes = score, image_bytes
            if score >= settings.FIDELITY_MIN_SCORE:
                break
    except (RenderFailed, ProviderNotConfigured) as exc:
        jobs.set_error(job_id, "RENDER_FAILED", str(exc))
        return
    assert best_bytes is not None
    jobs.artifact_path(job_id, "render").write_bytes(best_bytes)
    jobs.update(
        job_id,
        status=JobStatus.SUCCEEDED.value,
        error=None,
        fidelity_score=round(best_score, 4),
        fidelity_attempts=attempts,
    )


@router.post("/renders/{job_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_render(job_id: str) -> JSONResponse:
    record = jobs.get(job_id)
    if record is None:
        return job_not_found(job_id)

    if _select_adapter() is None:
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "RENDER_PROVIDER_NOT_CONFIGURED",
            "Set OPENROUTER_API_KEY or GEMINI_API_KEY to enable render generation.",
        )

    current = record["status"]
    if current == JobStatus.PROCESSING.value:
        return error_response(
            status.HTTP_409_CONFLICT,
            "JOB_ALREADY_RUNNING",
            "Render generation already in progress.",
        )
    if current == JobStatus.SUCCEEDED.value:
        return error_response(
            status.HTTP_409_CONFLICT,
            "JOB_ALREADY_SUCCEEDED",
            "Render generation already succeeded for this job.",
        )

    jobs.update(job_id, status=JobStatus.PROCESSING.value)
    thread = threading.Thread(target=_run_generation, args=(job_id,), daemon=True)
    thread.start()

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"id": job_id, "status": JobStatus.PROCESSING.value},
    )


@router.get("/files/{job_id}/{kind}")
def get_file(job_id: str, kind: str):
    if kind not in FILE_KINDS:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ARTIFACT_NOT_FOUND",
            f"No artifact '{kind}' for job '{job_id}'.",
        )
    path = jobs.artifact_path(job_id, kind)
    if not path.exists():
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ARTIFACT_NOT_FOUND",
            f"No artifact '{kind}' for job '{job_id}'.",
        )
    return FileResponse(path, media_type="image/png")
