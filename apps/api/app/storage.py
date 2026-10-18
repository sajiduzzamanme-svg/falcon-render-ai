"""Supabase Storage API client (server-side, secret key).

Used for render artifacts: uploads the full-resolution render into the
private ``renders`` bucket on completion, and mints time-limited signed
download URLs for authenticated downloads.

The secret server key travels in the ``apikey`` header (the verified
working pattern for ``sb_secret_...`` keys). It is read from env only
(``SUPABASE_URL`` / ``SUPABASE_SERVICE_KEY``), never logged, never
included in error messages.
"""

from __future__ import annotations

import httpx

from .adapters.http import http_client
from .config import settings


class StorageError(Exception):
    """Raised for Storage API failures. Messages never contain the key."""


class StorageClient:
    """Minimal Supabase Storage client. Stateless and thread-safe."""

    def __init__(self, base_url: str, service_key: str, timeout: float = 60.0):
        self._api = base_url.rstrip("/") + "/storage/v1"
        self._public_base = base_url.rstrip("/")
        self._key = service_key
        self._http: httpx.Client = http_client(timeout)

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"apikey": self._key}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "image/png",
        upsert: bool = True,
    ) -> dict:
        """Upload (or overwrite) an object. Returns the API response."""
        url = f"{self._api}/object/{bucket}/{path}"
        headers = self._headers(content_type)
        if upsert:
            headers["x-upsert"] = "true"
        try:
            resp = self._http.post(url, content=data, headers=headers)
        except httpx.HTTPError as exc:
            raise StorageError(
                f"Storage upload {bucket}/{path} failed: {type(exc).__name__}"
            ) from exc
        if resp.status_code >= 400:
            raise StorageError(
                f"Storage upload {bucket}/{path} -> HTTP {resp.status_code}: "
                f"{resp.text[:300]}"
            )
        return resp.json()

    def create_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """Mint a time-limited download URL. Returns the absolute URL."""
        url = f"{self._api}/object/sign/{bucket}/{path}"
        try:
            resp = self._http.post(
                url,
                json={"expiresIn": expires_in},
                headers=self._headers("application/json"),
            )
        except httpx.HTTPError as exc:
            raise StorageError(
                f"Storage sign {bucket}/{path} failed: {type(exc).__name__}"
            ) from exc
        if resp.status_code >= 400:
            raise StorageError(
                f"Storage sign {bucket}/{path} -> HTTP {resp.status_code}: "
                f"{resp.text[:300]}"
            )
        try:
            signed_path = resp.json()["signedURL"]
        except (ValueError, KeyError) as exc:
            raise StorageError("Storage sign returned an unexpected body.") from exc
        # signedURL is relative like "/object/sign/renders/<id>/render.png?token=..."
        return f"{self._public_base}/storage/v1{signed_path}"

    def close(self) -> None:
        self._http.close()


def get_storage_client() -> StorageClient | None:
    """Build a client from env, or None when Supabase is not configured."""
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY):
        return None
    return StorageClient(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
