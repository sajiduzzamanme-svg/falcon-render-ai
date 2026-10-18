"""Render job endpoints."""

import hashlib
import io
import logging
import threading
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw

from .. import credits
from ..adapters.base import ProviderNotConfigured, RenderAdapter, RenderFailed
from ..adapters.gemini import GeminiRenderAdapter
from ..adapters.openrouter import OpenRouterRenderAdapter
from ..auth import get_current_user, get_optional_user
from ..config import settings
from ..fidelity import FidelityError, fidelity_score
from ..geometry import GeometryError, extract_edges
from ..job_store import jobs
from ..schemas import (
    PRESETS,
    STYLES,
    JobStatus,
    RenderJobResponse,
    RenderListResponse,
)
from ..storage import get_storage_client
from ..supabase_client import is_configured

router = APIRouter()

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
FILE_KINDS = {"sketch", "edge", "render", "reference", "preview"}

PREVIEW_MAX_PX = 900
SIGNED_URL_TTL_SECONDS = 3600


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
    # owner_id lets the frontend decide download-button state before
    # attempting the gated endpoints (ADR 0004).
    detail["owner_id"] = record.get("user_id")
    detail["artifacts"] = {
        "sketch": f"/api/v1/files/{job_id}/sketch",
        "edge": f"/api/v1/files/{job_id}/edge",
        "reference": f"/api/v1/files/{job_id}/reference"
        if jobs.artifact_path(job_id, "reference").exists()
        else None,
        "render": f"/api/v1/files/{job_id}/render"
        if jobs.artifact_path(job_id, "render").exists()
        else None,
        "preview": f"/api/v1/files/{job_id}/preview"
        if jobs.artifact_path(job_id, "preview").exists()
        else None,
    }
    return detail


def _can_access_job(record: dict, user: dict) -> bool:
    """Ownership rule for full-resolution artifacts (ADR 0004).

    Only the job's owner may download. Jobs created anonymously
    (``user_id`` None) are NEVER downloadable by anyone — anonymous users
    get the watermarked preview only ("login chara download na").
    Job ids are unguessable UUIDs, so this is a sound gate.
    """
    owner = record.get("user_id")
    return owner is not None and owner == user["id"]


def _forbidden_download(record: dict) -> JSONResponse:
    """403 with an explanation matching why this job can't be downloaded."""
    if record.get("user_id") is None:
        message = (
            "This render was created without an account and cannot be "
            "downloaded. Create your own render to download it in full "
            "resolution."
        )
    else:
        message = "Only the account that created this render can download it."
    return error_response(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def _make_preview(src: Path, dst: Path) -> None:
    """Write a watermarked, downscaled preview of a finished render.

    Anonymous visitors see only this; the full-resolution file requires
    a signed-in session (signup gate).
    """
    with Image.open(src) as img:
        img = img.convert("RGB")
        img.thumbnail((PREVIEW_MAX_PX, PREVIEW_MAX_PX), Image.LANCZOS)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        banner_h = 34
        draw.rectangle(
            [0, img.height - banner_h, img.width, img.height],
            fill=(15, 23, 42, 130),
        )
        draw.text(
            (12, img.height - banner_h + 9),
            "FALCON RENDER AI \u00b7 PREVIEW",
            fill=(255, 255, 255, 235),
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        img.save(dst, "PNG")


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
    reference: Annotated[UploadFile | None, File()] = None,
    user: Annotated[dict | None, Depends(get_optional_user)] = None,
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

    record = jobs.create(
        preset=preset, style=style, user_id=user["id"] if user else None
    )
    job_id = record["id"]
    try:
        sketch_path = jobs.artifact_path(job_id, "sketch")
        sketch_path.write_bytes(content)
        edge_path = jobs.artifact_path(job_id, "edge")
        extract_edges(sketch_path, edge_path)
        if reference is not None:
            ref_content = await reference.read()
            validated_ref = _validate_image(ref_content, reference.filename)
            if isinstance(validated_ref, JSONResponse):
                return validated_ref
            jobs.artifact_path(job_id, "reference").write_bytes(ref_content)
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


def _run_generation(
    job_id: str, *, user_id: str | None = None, client_hash: str | None = None
) -> None:
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
    reference_path = jobs.artifact_path(job_id, "reference")
    reference_arg = reference_path if reference_path.exists() else None
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
                reference_path=reference_arg,
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
    render_path = jobs.artifact_path(job_id, "render")
    render_path.write_bytes(best_bytes)
    # Watermarked public preview (anonymous visitors see only this).
    try:
        _make_preview(render_path, jobs.artifact_path(job_id, "preview"))
    except Exception:
        logger.exception("Preview generation failed for job %s", job_id)
    # Mirror the full-resolution render into Supabase Storage (best-effort;
    # the download endpoint mints signed URLs from the bucket).
    if is_configured():
        try:
            storage = get_storage_client()
            if storage is not None:
                storage.upload("renders", f"{job_id}/render.png", best_bytes)
        except Exception:
            logger.exception("Storage upload failed for job %s", job_id)
    jobs.update(
        job_id,
        status=JobStatus.SUCCEEDED.value,
        error=None,
        fidelity_score=round(best_score, 4),
        fidelity_attempts=attempts,
    )
    # Credit settlement (ADR 0003): 10 credits per completed render, retries
    # free, failures never charged. Charging must never fail the render.
    try:
        credits.settle_job(
            job_id=job_id,
            succeeded=True,
            user_id=user_id,
            client_hash=client_hash,
        )
    except Exception:
        logger.exception("Credit settlement failed for job %s", job_id)


def _client_hash(request: Request) -> str:
    """Abuse-limited device/IP fingerprint for the anonymous free trial."""
    host = request.client.host if request.client else "unknown"
    return hashlib.sha256(host.encode("utf-8")).hexdigest()


@router.post("/renders/{job_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_render(
    job_id: str,
    request: Request,
    user: Annotated[dict | None, Depends(get_optional_user)] = None,
) -> JSONResponse:
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

    # Credit gate (ADR 0003): no-op when Supabase is not configured.
    client_hash = _client_hash(request)
    user_id = user["id"] if user else None
    try:
        credits.ensure_can_generate(user_id=user_id, client_hash=client_hash)
    except credits.InsufficientCredits as exc:
        return error_response(
            status.HTTP_402_PAYMENT_REQUIRED, "INSUFFICIENT_CREDITS", str(exc)
        )
    except credits.FreeTrialExhausted as exc:
        return error_response(
            status.HTTP_403_FORBIDDEN, "FREE_TRIAL_EXHAUSTED", str(exc)
        )

    jobs.update(job_id, status=JobStatus.PROCESSING.value)
    thread = threading.Thread(
        target=_run_generation,
        args=(job_id,),
        kwargs={"user_id": user_id, "client_hash": client_hash},
        daemon=True,
    )
    thread.start()

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"id": job_id, "status": JobStatus.PROCESSING.value},
    )


@router.get("/files/{job_id}/{kind}")
def get_file(
    job_id: str,
    kind: str,
    user: Annotated[dict | None, Depends(get_optional_user)] = None,
):
    if kind not in FILE_KINDS:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ARTIFACT_NOT_FOUND",
            f"No artifact '{kind}' for job '{job_id}'.",
        )
    # Signup gate: the full-resolution render needs a signed-in session,
    # and only the job's owner may access it (ADR 0004). Anonymous visitors
    # get the watermarked preview via /files/{id}/preview.
    if kind == "render":
        if user is None:
            return error_response(
                status.HTTP_401_UNAUTHORIZED,
                "UNAUTHORIZED",
                "Sign in to view full-resolution renders.",
            )
        record = jobs.get(job_id)
        if record is not None and not _can_access_job(record, user):
            return _forbidden_download(record)
    path = jobs.artifact_path(job_id, kind)
    if not path.exists():
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ARTIFACT_NOT_FOUND",
            f"No artifact '{kind}' for job '{job_id}'.",
        )
    return FileResponse(path, media_type="image/png")


@router.get("/renders/{job_id}/download")
def download_render(
    job_id: str,
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
) -> JSONResponse:
    """Mint a download URL for the full-resolution render.

    Requires a valid Supabase session (401 otherwise) AND ownership:
    only the account that created the job may download it (ADR 0004).
    Anonymous-created jobs are never downloadable — the watermarked
    preview is the only artifact for anonymous users.

    With Supabase configured, returns a time-limited signed Storage URL;
    in local-dev mode, the direct file URL (the caller still sends its
    token).
    """
    record = jobs.get(job_id)
    if record is None:
        return job_not_found(job_id)
    if not _can_access_job(record, user):
        return _forbidden_download(record)
    if not jobs.artifact_path(job_id, "render").exists():
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ARTIFACT_NOT_FOUND",
            f"No render artifact for job '{job_id}'.",
        )
    if is_configured():
        try:
            storage = get_storage_client()
            if storage is not None:
                url = storage.create_signed_url(
                    "renders",
                    f"{job_id}/render.png",
                    expires_in=SIGNED_URL_TTL_SECONDS,
                )
                return JSONResponse(
                    {
                        "download_url": url,
                        "expires_in": SIGNED_URL_TTL_SECONDS,
                    }
                )
        except Exception:
            logger.exception(
                "Signed URL minting failed for job %s; falling back", job_id
            )
    base = str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "download_url": f"{base}/api/v1/files/{job_id}/render",
            "expires_in": None,
        }
    )
