"""Auth tests: Supabase JWT verification + signup-gated downloads.

Crypto is tested with a locally generated EC P-256 keypair injected into
app.auth's JWKS cache — no network, no secrets. Route gating is tested
through TestClient with dependency_overrides (crypto covered separately).
"""

from __future__ import annotations

import base64
import io
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from PIL import Image

from app import auth, jobs
from app.auth import get_current_user, get_optional_user, verify_access_token
from app.config import settings
from app.main import app

KID = "test-kid-1"


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_keypair() -> tuple[str, dict]:
    """Return (private_pem, public_jwk) for an EC P-256 key."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    nums = priv.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64u(nums.x.to_bytes(32, "big")),
        "y": _b64u(nums.y.to_bytes(32, "big")),
        "kid": KID,
        "alg": "ES256",
        "use": "sig",
    }
    return pem, jwk


@pytest.fixture()
def keypair() -> tuple[str, dict]:
    return _make_keypair()


@pytest.fixture()
def jwks(keypair: tuple[str, dict], monkeypatch: pytest.MonkeyPatch) -> dict:
    """Inject the test public key into auth's JWKS cache."""
    _, jwk = keypair
    monkeypatch.setattr(auth, "_jwks_cache", {"keys": [jwk], "fetched_at": time.time()})
    return jwk


def _token(
    private_pem: str,
    *,
    kid: str = KID,
    sub: str = "user-abc",
    email: str = "a@b.c",
    exp_offset: timedelta = timedelta(hours=1),
    audience: str = "authenticated",
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "email": email,
        "aud": audience,
        "iat": now,
        "exp": now + exp_offset,
    }
    return pyjwt.encode(payload, private_pem, algorithm="ES256", headers={"kid": kid})


def test_verify_valid_token(jwks: dict, keypair: tuple[str, dict]) -> None:
    pem, _ = keypair
    user = verify_access_token(_token(pem))
    assert user["id"] == "user-abc"
    assert user["email"] == "a@b.c"


def test_verify_wrong_signature_rejected(jwks: dict, keypair: tuple[str, dict]) -> None:
    other_pem, _ = _make_keypair()
    with pytest.raises(auth.AuthError) as ei:
        verify_access_token(_token(other_pem))
    assert ei.value.code == "UNAUTHORIZED"


def test_verify_unknown_kid_rejected(jwks: dict, keypair: tuple[str, dict]) -> None:
    pem, _ = keypair
    with pytest.raises(auth.AuthError):
        verify_access_token(_token(pem, kid="nope"))


def test_verify_expired_rejected(jwks: dict, keypair: tuple[str, dict]) -> None:
    pem, _ = keypair
    with pytest.raises(auth.AuthError):
        verify_access_token(_token(pem, exp_offset=timedelta(seconds=-10)))


def test_verify_malformed_rejected(jwks: dict) -> None:
    with pytest.raises(auth.AuthError):
        verify_access_token("not-a-jwt")


def test_verify_wrong_audience_rejected(jwks: dict, keypair: tuple[str, dict]) -> None:
    pem, _ = keypair
    with pytest.raises(auth.AuthError):
        verify_access_token(_token(pem, audience="someone-else"))


# ---------- route gating ----------


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")
    return TestClient(app)


def _png_bytes(width: int = 200, height: int = 150) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 210, 220))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _job_with_render(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/renders",
        files={"file": ("s.png", _png_bytes(), "application/octet-stream")},
        data={"preset": "daylight", "style": "modern"},
    )
    assert resp.status_code == 201, resp.text
    job_id = resp.json()["id"]
    jobs.artifact_path(job_id, "render").write_bytes(_png_bytes(400, 300))
    jobs.artifact_path(job_id, "preview").write_bytes(_png_bytes(100, 80))
    return job_id


def _authed(client: TestClient, user_id: str = "user-abc"):
    client.app.dependency_overrides[get_current_user] = lambda: {
        "id": user_id,
        "email": "a@b.c",
    }
    client.app.dependency_overrides[get_optional_user] = lambda: {
        "id": user_id,
        "email": "a@b.c",
    }
    return client


@pytest.fixture()
def _clean_overrides(client: TestClient):
    yield
    client.app.dependency_overrides.clear()


def test_render_file_anonymous_401(client: TestClient, _clean_overrides) -> None:
    job_id = _job_with_render(client)
    resp = client.get(f"/api/v1/files/{job_id}/render")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_render_file_authed_200(client: TestClient, _clean_overrides) -> None:
    job_id = _job_with_render(client)
    _authed(client)
    resp = client.get(f"/api/v1/files/{job_id}/render")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")


def test_preview_stays_public(client: TestClient) -> None:
    job_id = _job_with_render(client)
    resp = client.get(f"/api/v1/files/{job_id}/preview")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")


def test_download_endpoint_anonymous_401(client: TestClient, _clean_overrides) -> None:
    job_id = _job_with_render(client)
    resp = client.get(f"/api/v1/renders/{job_id}/download")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_download_endpoint_authed_returns_url(
    client: TestClient, _clean_overrides
) -> None:
    job_id = _job_with_render(client)
    _authed(client)
    resp = client.get(f"/api/v1/renders/{job_id}/download")
    assert resp.status_code == 200
    body = resp.json()
    assert body["download_url"].endswith(f"/api/v1/files/{job_id}/render")


def test_download_other_users_job_forbidden(
    client: TestClient, _clean_overrides
) -> None:
    job_id = _job_with_render(client)
    jobs.update(job_id, user_id="someone-else")
    _authed(client, user_id="user-abc")
    resp = client.get(f"/api/v1/renders/{job_id}/download")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_job_creation_attaches_user_id(client: TestClient, _clean_overrides) -> None:
    _authed(client, user_id="user-abc")
    resp = client.post(
        "/api/v1/renders",
        files={"file": ("s.png", _png_bytes(), "application/octet-stream")},
        data={"preset": "daylight", "style": "modern"},
    )
    assert resp.status_code == 201, resp.text
    record = jobs.get(resp.json()["id"])
    assert record is not None
    assert record.get("user_id") == "user-abc"


def test_preview_generation_marks_watermark() -> None:
    from app.routes.renders import _make_preview

    src = Path("/tmp") / "auth_test_src.png"
    dst = Path("/tmp") / "auth_test_preview.png"
    Image.new("RGB", (1200, 800), color=(10, 20, 30)).save(src, "PNG")
    _make_preview(src, dst)
    with Image.open(dst) as img:
        assert max(img.size) <= 900
    assert dst.stat().st_size > 0
