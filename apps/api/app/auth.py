"""Supabase Auth JWT verification (signup-gated downloads).

Verifies Supabase-issued user access JWTs against the project's JWKS
(``SUPABASE_JWKS_URL``, defaulting to the Falcon Render AI project). The
``sub`` claim becomes the ``user_id`` used for jobs/credits.

No secrets live here: user access tokens are asymmetric-key signed (ES256),
so verification needs only the *public* JWKS. The server secret key is
never touched by this module.

Usage in routes::

    from ..auth import get_current_user, get_optional_user

    @router.get("/renders/{job_id}/download")
    def download(job_id: str, user: dict = Depends(get_current_user)): ...

``get_current_user`` raises 401 on missing/invalid/expired tokens.
``get_optional_user`` returns ``None`` for anonymous callers but still
raises 401 when a token is present and invalid.
"""

from __future__ import annotations

import logging
import time
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .adapters.http import http_client
from .config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_JWKS_TTL_SECONDS = 3600

# Module-level cache: {"keys": [...], "fetched_at": float}. Tests inject
# directly; production refreshes from SUPABASE_JWKS_URL on expiry.
_jwks_cache: dict = {}


def _fetch_jwks() -> list[dict]:
    """Download the JWKS document. Raises AuthError on failure."""
    client = http_client(timeout=15.0)
    try:
        resp = client.get(settings.SUPABASE_JWKS_URL)
    except Exception as exc:
        raise AuthError(
            "AUTH_UNAVAILABLE", "Could not reach the auth key server."
        ) from exc
    finally:
        client.close()
    if resp.status_code != 200:
        raise AuthError(
            "AUTH_UNAVAILABLE",
            f"Auth key server returned HTTP {resp.status_code}.",
        )
    try:
        keys = resp.json().get("keys", [])
    except ValueError as exc:
        raise AuthError(
            "AUTH_UNAVAILABLE", "Auth key server returned bad JSON."
        ) from exc
    if not keys:
        raise AuthError("AUTH_UNAVAILABLE", "Auth key server returned no keys.")
    return keys


def _get_jwks() -> list[dict]:
    """Cached JWKS, refreshing on expiry. Falls back to stale on error."""
    now = time.time()
    cached = _jwks_cache.get("keys")
    fetched_at = _jwks_cache.get("fetched_at", 0.0)
    if cached and now - fetched_at < _JWKS_TTL_SECONDS:
        return cached
    try:
        keys = _fetch_jwks()
    except AuthError:
        if cached:
            logger.warning("JWKS refresh failed; using stale cached keys")
            return cached
        raise
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def _key_for_kid(kid: str | None, keys: list[dict]):
    """Build a PyJWT-ready key from the JWK matching ``kid``."""
    for jwk in keys:
        if jwk.get("kid") == kid:
            alg = jwk.get("alg", "ES256")
            return jwt.algorithms.ECAlgorithm.from_jwk(jwk), alg
    raise AuthError("UNAUTHORIZED", "Token was signed by an unknown key.")


class AuthError(Exception):
    """Authentication failure. Carries an app-style error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def verify_access_token(token: str) -> dict:
    """Verify a Supabase access JWT; return ``{"id": sub, "email": ...}``.

    Raises AuthError on any failure (bad signature, expiry, audience, ...).
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthError("UNAUTHORIZED", "Malformed access token.") from exc
    key, alg = _key_for_kid(header.get("kid"), _get_jwks())
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[alg],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("UNAUTHORIZED", "Access token has expired.") from exc
    except jwt.InvalidAudienceError as exc:
        raise AuthError("UNAUTHORIZED", "Access token has wrong audience.") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("UNAUTHORIZED", "Invalid access token.") from exc
    return {"id": claims["sub"], "email": claims.get("email")}


def _unauthorized(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials or None


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
) -> dict:
    """FastAPI dependency: require a valid Supabase session. 401 otherwise."""
    token = _extract_token(credentials)
    if not token:
        raise _unauthorized()
    try:
        return verify_access_token(token)
    except AuthError as exc:
        raise _unauthorized(exc.message) from exc


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
) -> dict | None:
    """FastAPI dependency: user dict or None. 401 when a token is invalid."""
    token = _extract_token(credentials)
    if not token:
        return None
    try:
        return verify_access_token(token)
    except AuthError as exc:
        raise _unauthorized(exc.message) from exc
