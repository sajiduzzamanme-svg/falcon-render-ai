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
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    STORAGE_DIR: Path = REPO_ROOT / "storage"
    MAX_UPLOAD_MB: int = 10


settings = Settings()
