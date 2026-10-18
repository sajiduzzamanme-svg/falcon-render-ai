"""Health check."""

from fastapi import APIRouter

from ..adapters.gemini import GeminiRenderAdapter
from ..adapters.openrouter import OpenRouterRenderAdapter
from ..schemas import HealthResponse
from .renders import _select_adapter

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    adapter = _select_adapter()
    provider: str = "unconfigured"
    if isinstance(adapter, OpenRouterRenderAdapter):
        provider = "openrouter"
    elif isinstance(adapter, GeminiRenderAdapter):
        provider = "gemini"
    return HealthResponse(version="0.1.0", geometry="opencv", render_provider=provider)  # type: ignore[arg-type]
