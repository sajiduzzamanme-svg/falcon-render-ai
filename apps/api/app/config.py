"""Application settings.

Never log or return GEMINI_API_KEY.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# <repo-root>/storage — app/config.py -> parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash-image"
    # Fidelity gate: render is retried (up to FIDELITY_MAX_ATTEMPTS) while the
    # edge-recall score is below FIDELITY_MIN_SCORE; the best attempt is kept.
    # 0.0 disables the gate (score is still recorded). Each retry costs one
    # provider call — calibrate FIDELITY_MIN_SCORE from real renders first
    # (initial data: faithful ~0.66, visibly drifted ~0.45).
    FIDELITY_MIN_SCORE: float = 0.0
    FIDELITY_MAX_ATTEMPTS: int = 3
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    STORAGE_DIR: Path = REPO_ROOT / "storage"
    MAX_UPLOAD_MB: int = 10


settings = Settings()
