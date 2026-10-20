"""Pydantic v2 request/response models."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

Preset = Literal["daylight", "dusk", "night"]
Style = Literal["modern", "minimalist", "warm"]

PRESETS: tuple[str, ...] = ("daylight", "dusk", "night")
STYLES: tuple[str, ...] = ("modern", "minimalist", "warm")

# Job modes: exterior sketch->render, or interior blank-room->design.
Mode = Literal["exterior", "interior"]
MODES: tuple[str, ...] = ("exterior", "interior")
INTERIOR_STYLES: tuple[str, ...] = (
    "modern",
    "scandinavian",
    "minimalist",
    "luxury",
    "traditional",
)
ROOM_TYPES: tuple[str, ...] = (
    "drawing",
    "living",
    "dining",
    "master_bedroom",
    "child_bedroom",
    "bedroom",
    "kitchen",
    "bathroom",
    "office",
)


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    geometry: str = "opencv"
    render_provider: Literal["gemini", "openrouter", "unconfigured"]
    # Deployed git commit (Railway sets RAILWAY_GIT_COMMIT_SHA; local dev
    # falls back to git rev-parse). Lets us verify which commit is live.
    commit: str = "unknown"


class RenderCreateResponse(BaseModel):
    id: str
    status: JobStatus
    preset: str
    style: str
    mode: str = "exterior"
    room_type: str | None = None
    created_at: datetime


class Artifacts(BaseModel):
    sketch: str
    edge: str
    reference: str | None = None
    render: str | None = None
    preview: str | None = None


class RenderJobResponse(BaseModel):
    id: str
    status: JobStatus
    preset: str
    style: str
    mode: str = "exterior"
    room_type: str | None = None
    created_at: datetime
    updated_at: datetime
    error: ErrorDetail | None = None
    artifacts: Artifacts
    fidelity_score: float | None = None
    fidelity_attempts: int = 0
    # UUID of the creating account, or None for anonymous jobs.
    # Lets the frontend decide download-button state (ADR 0004).
    owner_id: str | None = None


class MeResponse(BaseModel):
    id: str
    email: str | None = None
    # Credit balance; None when Supabase is not configured (local dev).
    credits: int | None = None


class RenderJobSummary(BaseModel):
    id: str
    status: JobStatus
    preset: str
    style: str
    mode: str = "exterior"
    room_type: str | None = None
    created_at: datetime
    updated_at: datetime
    fidelity_score: float | None = None


class RenderListResponse(BaseModel):
    items: list[RenderJobSummary] = Field(default_factory=list)
    total: int = 0


class GenerateResponse(BaseModel):
    id: str
    status: JobStatus
