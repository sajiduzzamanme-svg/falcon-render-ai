"""Supabase PostgREST client.

The secret server key travels in the ``apikey`` header. This is the verified
working pattern for the new ``sb_secret_...`` keys (see
``custom.supabase`` connector doc): the gateway requires ``apikey``, and the
secret key in that header bypasses RLS. Do NOT use the legacy
``service_role`` JWT here — Supabase reads the role from the
``Authorization`` header, not ``apikey``, so the legacy JWT alone does not
bypass RLS.

HTTP goes through ``adapters.http.http_client`` (``trust_env=False`` +
explicit proxy): some environments export proxy vars that crash httpx's
env-proxy parsing.

The key is never logged, never included in error messages, and never written
anywhere: it lives in process env (``SUPABASE_SERVICE_KEY``) only.
"""

from __future__ import annotations

import httpx

from .adapters.http import http_client
from .config import settings


class SupabaseError(Exception):
    """Raised for Supabase REST failures. Messages never contain the key."""


class SupabaseClient:
    """Minimal PostgREST client. Stateless and thread-safe."""

    def __init__(self, base_url: str, service_key: str, timeout: float = 30.0):
        self._base = base_url.rstrip("/") + "/rest/v1"
        self._key = service_key
        self._http: httpx.Client = http_client(timeout)

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        headers = {"apikey": self._key, "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(
        self,
        method: str,
        table: str,
        params: dict | None = None,
        payload: dict | None = None,
        prefer: str | None = None,
    ) -> list:
        url = f"{self._base}/{table}"
        try:
            resp = self._http.request(
                method,
                url,
                params=params,
                json=payload,
                headers=self._headers(prefer),
            )
        except httpx.HTTPError as exc:
            # Never include headers (the key) — only the failure kind.
            raise SupabaseError(
                f"Supabase {method} {table} failed: {type(exc).__name__}"
            ) from exc
        if resp.status_code >= 400:
            raise SupabaseError(
                f"Supabase {method} {table} -> HTTP {resp.status_code}: "
                f"{resp.text[:300]}"
            )
        if resp.status_code == 204 or not resp.content.strip():
            return []
        try:
            data = resp.json()
        except ValueError as exc:
            raise SupabaseError(
                f"Supabase {method} {table} returned non-JSON body"
            ) from exc
        return data if isinstance(data, list) else [data]

    def select(self, table: str, params: dict | None = None) -> list[dict]:
        return self._request("GET", table, params=params)

    def insert(
        self, table: str, payload: dict, prefer: str = "return=representation"
    ) -> list[dict]:
        return self._request("POST", table, payload=payload, prefer=prefer)

    def update(
        self, table: str, values: dict, params: dict | None = None
    ) -> list[dict]:
        return self._request(
            "PATCH",
            table,
            params=params,
            payload=values,
            prefer="return=representation",
        )

    def delete(self, table: str, params: dict | None = None) -> list[dict]:
        return self._request("DELETE", table, params=params)

    def close(self) -> None:
        self._http.close()


def is_configured() -> bool:
    """True when Supabase env vars are present (selects the Supabase store)."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)


def get_client() -> SupabaseClient | None:
    """Build a client from env, or None when Supabase is not configured."""
    if not is_configured():
        return None
    return SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
