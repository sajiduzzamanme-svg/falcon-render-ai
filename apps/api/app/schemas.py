"""Pydantic v2 request/response models."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

Preset = Literal["daylight", "dusk", "night"]
Style = Literal["modern", "minimalist", "warm"]

PRESETS: tuple[str, ...] = ("daylight", "dusk", "night")
STYLES: tuple[str, ...] = ("modern", "minimalist", "warm")


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


class RenderCreateResponse(BaseModel):
    id: str
    status: JobStatus
    preset: str
    style: str
    created_at: datetime


class Artifacts(BaseModel):
    sketch: str
    edge: str
    render: str | None = None


class RenderJobResponse(BaseModel):
    id: str
    status: JobStatus
    preset: str
    style: str
    created_at: datetime
    updated_at: datetime
    error: ErrorDetail | None = None
    artifacts: Artifacts


class RenderJobSummary(BaseModel):
    id: str
    status: JobStatus
    preset: str
    style: str
    created_at: datetime
    updated_at: datetime


class RenderListResponse(BaseModel):
    items: list[RenderJobSummary] = Field(default_factory=list)
    total: int = 0


class GenerateResponse(BaseModel):
    id: str
    status: JobStatus
