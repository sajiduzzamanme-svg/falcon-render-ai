"""Health check."""

from fastapi import APIRouter

from ..adapters.gemini import GeminiRenderAdapter
from ..config import settings
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    provider: str = (
        "gemini"
        if GeminiRenderAdapter(settings.GEMINI_API_KEY).configured
        else "unconfigured"
    )
    return HealthResponse(version="0.1.0", geometry="opencv", render_provider=provider)  # type: ignore[arg-type]
