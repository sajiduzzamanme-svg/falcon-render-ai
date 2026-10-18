"""Gemini (Nano Banana family) render adapter via REST.

Endpoint: gemini-2.5-flash-image:generateContent
Auth: `x-goog-api-key` header. No key -> ProviderNotConfigured (surfaces as
HTTP 503 RENDER_PROVIDER_NOT_CONFIGURED). Never fake a render.
"""

import base64
from pathlib import Path

import httpx

from .base import ProviderNotConfigured, RenderAdapter, RenderFailed
from .http import http_client

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-image:generateContent"
)
_TIMEOUT_S = 120

_PRESET_LIGHTING = {
    "daylight": "bright natural daylight with a clear sky",
    "dusk": "warm golden-hour light, with interior lights on",
    "night": "a night scene with artificial lighting",
}
_STYLE_DIRECTION = {
    "modern": "contemporary design with clean lines",
    "minimalist": "minimal design with white surfaces",
    "warm": "warm materials with wood accents",
}


def fidelity_prompt(preset: str, style: str, has_reference: bool = False) -> str:
    lighting = _PRESET_LIGHTING.get(preset, preset)
    look = _STYLE_DIRECTION.get(style, style)
    prompt = (
        "Render this architectural sketch into a photorealistic image. "
        "Preserve the exact geometry, massing, proportions, window and door "
        "placement, and viewpoint of the provided sketch and edge map — "
        "do not redesign, reinterpret, or alter any structural element. "
        f"Lighting: {lighting}. Style: {look}."
    )
    if has_reference:
        prompt += (
            " A third image is provided as a STYLE reference only: take "
            "materials, colors, and mood from it, but never its geometry, "
            "layout, or viewpoint."
        )
    return prompt


class GeminiRenderAdapter(RenderAdapter):
    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def generate(
        self,
        sketch_path: Path,
        edge_path: Path,
        preset: str,
        style: str,
        reference_path: Path | None = None,
    ) -> bytes:
        if not self.configured:
            raise ProviderNotConfigured(
                "Set GEMINI_API_KEY to enable render generation."
            )

        def _b64(path: Path) -> str:
            return base64.b64encode(path.read_bytes()).decode("ascii")

        parts: list[dict] = [
            {
                "text": fidelity_prompt(
                    preset, style, has_reference=reference_path is not None
                )
            },
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": _b64(sketch_path),
                }
            },
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": _b64(edge_path),
                }
            },
        ]
        if reference_path is not None:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": _b64(reference_path),
                    }
                }
            )

        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }

        try:
            with http_client(_TIMEOUT_S) as client:
                resp = client.post(
                    _ENDPOINT,
                    headers={"x-goog-api-key": self._api_key},
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise RenderFailed(f"Gemini request failed: {exc}") from exc

        if resp.status_code >= 400:
            detail = _provider_message(resp)
            raise RenderFailed(f"Gemini API error {resp.status_code}: {detail}")

        data = _extract_image(resp.json())
        if data is None:
            raise RenderFailed("Gemini returned no image data.")
        return data


def _provider_message(resp: httpx.Response) -> str:
    """Extract a human-readable provider message; never include key material."""
    try:
        payload = resp.json()
        err = payload.get("error", {})
        return str(err.get("message") or resp.text)[:500]
    except (ValueError, AttributeError):
        return resp.text[:500]


def _extract_image(payload: dict) -> bytes | None:
    for cand in payload.get("candidates", []):
        content = cand.get("content", {})
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                try:
                    return base64.b64decode(inline["data"])
                except (ValueError, TypeError):
                    continue
    return None
