"""Render adapter interface."""

from abc import ABC, abstractmethod
from pathlib import Path


class ProviderNotConfigured(Exception):
    """Raised when the provider cannot run (e.g. missing API key)."""


class RenderFailed(Exception):
    """Raised when the provider call fails. Message only — never key material."""


class RenderAdapter(ABC):
    @abstractmethod
    def generate(
        self, sketch_path: Path, edge_path: Path, preset: str, style: str
    ) -> bytes:
        """Render sketch+edge map into image bytes (PNG)."""
