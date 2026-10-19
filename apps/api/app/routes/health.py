"""Health check."""

import os
import subprocess

from fastapi import APIRouter

from ..adapters.gemini import GeminiRenderAdapter
from ..adapters.openrouter import OpenRouterRenderAdapter
from ..schemas import HealthResponse
from .renders import _select_adapter

router = APIRouter()


def _commit_sha() -> str:
    """Deployed commit SHA for verifying which code is live."""
    sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA") or os.environ.get("GIT_SHA")
    if sha:
        return sha[:12]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    adapter = _select_adapter()
    provider: str = "unconfigured"
    if isinstance(adapter, OpenRouterRenderAdapter):
        provider = "openrouter"
    elif isinstance(adapter, GeminiRenderAdapter):
        provider = "gemini"
    return HealthResponse(version="0.1.0", geometry="opencv", render_provider=provider, commit=_commit_sha())  # type: ignore[arg-type]
