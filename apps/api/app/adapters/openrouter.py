"""OpenRouter render adapter (OpenAI-compatible chat completions).

Routes to image-capable models (default: google/gemini-2.5-flash-image,
the Nano Banana family) with the sketch + edge map as image inputs and
`modalities: ["image", "text"]` so the provider returns image bytes.
Auth: `Authorization: Bearer` header. No key -> ProviderNotConfigured
(surfaces as HTTP 503 RENDER_PROVIDER_NOT_CONFIGURED). Never fake a render.
"""

import base64
from pathlib import Path

import httpx

from .base import ProviderNotConfigured, RenderAdapter, RenderFailed
from .gemini import fidelity_prompt
from .http import http_client

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT_S = 180


class OpenRouterRenderAdapter(RenderAdapter):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def generate(
        self, sketch_path: Path, edge_path: Path, preset: str, style: str
    ) -> bytes:
        if not self.configured:
            raise ProviderNotConfigured(
                "Set OPENROUTER_API_KEY to enable render generation."
            )

        def _data_url(path: Path) -> str:
            raw = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{raw}"

        body = {
            "model": self._model,
            "modalities": ["image", "text"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": fidelity_prompt(preset, style)},
                        {
                            "type": "image_url",
                            "image_url": {"url": _data_url(sketch_path)},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": _data_url(edge_path)},
                        },
                    ],
                }
            ],
        }

        try:
            with http_client(_TIMEOUT_S) as client:
                resp = client.post(
                    _ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "HTTP-Referer": "https://falcon-render-ai.local",
                        "X-Title": "Falcon Render AI",
                    },
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise RenderFailed(f"OpenRouter request failed: {exc}") from exc

        if resp.status_code >= 400:
            detail = _provider_message(resp)
            raise RenderFailed(f"OpenRouter API error {resp.status_code}: {detail}")

        data = _extract_image(resp.json())
        if data is None:
            raise RenderFailed("OpenRouter returned no image data.")
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
    for choice in payload.get("choices", []):
        images = (choice.get("message") or {}).get("images") or []
        for image in images:
            url = (image.get("image_url") or {}).get("url", "")
            if url.startswith("data:image/") and "," in url:
                b64 = url.split(",", 1)[1]
                try:
                    return base64.b64decode(b64)
                except (ValueError, TypeError):
                    continue
    return None
