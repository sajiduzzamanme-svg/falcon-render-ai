"""API contract tests (TestClient). STORAGE_DIR is isolated per test."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import jobs
from app.config import settings
from app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    # Force the JSON store: these contract tests must not touch live Supabase
    # even if SUPABASE_* env vars happen to be set.
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")
    return TestClient(app)


def _png_bytes(width: int = 200, height: int = 150) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 210, 220))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload(
    client: TestClient,
    content: bytes,
    filename: str = "sketch.png",
    preset: str = "daylight",
    style: str = "modern",
):
    return client.post(
        "/api/v1/renders",
        files={"file": (filename, content, "application/octet-stream")},
        data={"preset": preset, "style": style},
    )


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["geometry"] == "opencv"
    assert body["render_provider"] == "unconfigured"


def test_upload_valid_creates_job_and_edges(client: TestClient) -> None:
    resp = _upload(client, _png_bytes())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["preset"] == "daylight"
    assert body["style"] == "modern"
    assert "id" in body and "created_at" in body

    job_id = body["id"]
    assert jobs.artifact_path(job_id, "sketch").exists()
    edge = jobs.artifact_path(job_id, "edge")
    assert edge.exists() and edge.stat().st_size > 0


def test_upload_txt_rejected(client: TestClient) -> None:
    resp = _upload(client, b"hello world", filename="notes.txt")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_UPLOAD"


def test_upload_too_large_rejected(client: TestClient) -> None:
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (10 * 1024 * 1024 + 1)
    resp = _upload(client, big, filename="big.png")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_UPLOAD"


def test_upload_bad_preset(client: TestClient) -> None:
    resp = _upload(client, _png_bytes(), preset="sunset")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_PRESET"


def test_upload_bad_style(client: TestClient) -> None:
    resp = _upload(client, _png_bytes(), style="baroque")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_STYLE"


def test_generate_without_key_returns_503(client: TestClient) -> None:
    job_id = _upload(client, _png_bytes()).json()["id"]
    resp = client.post(f"/api/v1/renders/{job_id}/generate")
    assert resp.status_code == 503
    body = resp.json()["error"]
    assert body["code"] == "RENDER_PROVIDER_NOT_CONFIGURED"
    assert "GEMINI_API_KEY" in body["message"]


def test_generate_unknown_id(client: TestClient) -> None:
    resp = client.post("/api/v1/renders/nope/generate")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_get_unknown_id(client: TestClient) -> None:
    resp = client.get("/api/v1/renders/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_get_render_includes_artifact_urls(client: TestClient) -> None:
    job_id = _upload(client, _png_bytes()).json()["id"]
    body = client.get(f"/api/v1/renders/{job_id}").json()
    assert body["artifacts"]["sketch"] == f"/api/v1/files/{job_id}/sketch"
    assert body["artifacts"]["edge"] == f"/api/v1/files/{job_id}/edge"
    assert body["artifacts"]["render"] is None


def test_list_renders_newest_first(client: TestClient) -> None:
    first = _upload(client, _png_bytes(), style="warm").json()["id"]
    second = _upload(client, _png_bytes(), style="minimalist").json()["id"]
    body = client.get("/api/v1/renders").json()
    assert body["total"] == 2
    assert body["items"][0]["id"] == second
    assert body["items"][1]["id"] == first


def test_file_download_sketch_and_edge(client: TestClient) -> None:
    job_id = _upload(client, _png_bytes()).json()["id"]
    for kind in ("sketch", "edge"):
        resp = client.get(f"/api/v1/files/{job_id}/{kind}")
        assert resp.status_code == 200, kind
        assert resp.headers["content-type"].startswith("image/")
        assert len(resp.content) > 0


def test_render_before_generation_404(client: TestClient) -> None:
    job_id = _upload(client, _png_bytes()).json()["id"]
    # Anonymous callers are gated before the artifact check.
    resp = client.get(f"/api/v1/files/{job_id}/render")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"
    # ADR 0004: ownership is checked before existence — an anonymous job is
    # never downloadable, so a signed-in caller gets 403 even when the
    # render artifact does not exist yet.
    from app.auth import get_optional_user

    client.app.dependency_overrides[get_optional_user] = lambda: {"id": "u1"}
    try:
        resp = client.get(f"/api/v1/files/{job_id}/render")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
    finally:
        client.app.dependency_overrides.clear()


def test_double_generate_guard_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    job_id = _upload(client, _png_bytes()).json()["id"]
    jobs.update(job_id, status="processing")
    resp = client.post(f"/api/v1/renders/{job_id}/generate")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "JOB_ALREADY_RUNNING"


def test_generate_succeeded_guard_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    job_id = _upload(client, _png_bytes()).json()["id"]
    jobs.update(job_id, status="succeeded")
    resp = client.post(f"/api/v1/renders/{job_id}/generate")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "JOB_ALREADY_SUCCEEDED"


def test_openrouter_adapter_selection_prefers_openrouter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.gemini import GeminiRenderAdapter
    from app.adapters.openrouter import OpenRouterRenderAdapter
    from app.routes.renders import _select_adapter

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    adapter = _select_adapter()
    assert isinstance(adapter, OpenRouterRenderAdapter)

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    adapter = _select_adapter()
    assert isinstance(adapter, GeminiRenderAdapter)

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert _select_adapter() is None


def test_health_reports_openrouter_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    resp = client.get("/api/v1/health")
    assert resp.json()["render_provider"] == "openrouter"


def test_generate_with_openrouter_key_succeeds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    from app.adapters.openrouter import OpenRouterRenderAdapter

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(
        OpenRouterRenderAdapter, "generate", lambda self, *a, **k: _png_bytes(400, 300)
    )
    job_id = _upload(client, _png_bytes()).json()["id"]
    resp = client.post(f"/api/v1/renders/{job_id}/generate")
    assert resp.status_code == 202
    body = {}
    for _ in range(100):
        body = client.get(f"/api/v1/renders/{job_id}").json()
        if body["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert body["status"] == "succeeded"
    assert body["fidelity_score"] is not None
    assert 0.0 <= body["fidelity_score"] <= 1.0
    assert body["fidelity_attempts"] >= 1
    # The full-resolution file endpoint is signup-gated: anonymous -> 401.
    resp = client.get(f"/api/v1/files/{job_id}/render")
    assert resp.status_code == 401
    from app.auth import get_optional_user

    # ADR 0004: only the owner may download. This job was created
    # anonymously, so a signed-in user gets 403 — recreate the flow as the
    # owner for the 200 case.
    client.app.dependency_overrides[get_optional_user] = lambda: {"id": "u1"}
    try:
        resp = client.get(f"/api/v1/files/{job_id}/render")
        assert resp.status_code == 403
        # Owner flow: upload as u1, then the full-res file is accessible.
        owner_job = _upload(client, _png_bytes()).json()["id"]
        jobs.artifact_path(owner_job, "render").write_bytes(_png_bytes(400, 300))
        resp = client.get(f"/api/v1/files/{owner_job}/render")
        assert resp.status_code == 200
        # A watermarked preview was generated alongside the render.
        resp = client.get(f"/api/v1/files/{job_id}/preview")
        assert resp.status_code == 200
    finally:
        client.app.dependency_overrides.clear()


def test_fidelity_gate_retries_until_max_attempts(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    from app.adapters.openrouter import OpenRouterRenderAdapter

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "FIDELITY_MIN_SCORE", 0.99)
    monkeypatch.setattr(settings, "FIDELITY_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(
        OpenRouterRenderAdapter, "generate", lambda self, *a, **k: b"fake-png-bytes"
    )
    job_id = _upload(client, _png_bytes()).json()["id"]
    assert client.post(f"/api/v1/renders/{job_id}/generate").status_code == 202
    body = {}
    for _ in range(100):
        body = client.get(f"/api/v1/renders/{job_id}").json()
        if body["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert body["status"] == "succeeded"
    assert body["fidelity_attempts"] == 3
    assert body["fidelity_score"] == pytest.approx(0.0)


def test_upload_with_reference_stores_artifact(
    client: TestClient,
) -> None:
    resp = client.post(
        "/api/v1/renders",
        files={
            "file": ("sketch.png", _png_bytes(), "application/octet-stream"),
            "reference": ("ref.png", _png_bytes(), "application/octet-stream"),
        },
        data={"preset": "dusk", "style": "warm"},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]
    detail = client.get(f"/api/v1/renders/{job_id}").json()
    assert detail["artifacts"]["reference"] is not None
    assert detail["artifacts"]["reference"].endswith(f"/{job_id}/reference")
    r = client.get(f"/api/v1/files/{job_id}/reference")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_upload_without_reference_has_null_artifact(
    client: TestClient,
) -> None:
    job_id = _upload(client, _png_bytes()).json()["id"]
    detail = client.get(f"/api/v1/renders/{job_id}").json()
    assert detail["artifacts"]["reference"] is None
    r = client.get(f"/api/v1/files/{job_id}/reference")
    assert r.status_code == 404


def test_upload_invalid_reference_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/renders",
        files={
            "file": ("sketch.png", _png_bytes(), "application/octet-stream"),
            "reference": ("evil.txt", b"not an image", "text/plain"),
        },
        data={"preset": "daylight", "style": "modern"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_UPLOAD"


def _upload_interior(
    client: TestClient,
    content: bytes,
    style: str = "scandinavian",
    room_type: str = "bedroom",
):
    return client.post(
        "/api/v1/renders",
        files={"file": ("room.png", content, "application/octet-stream")},
        data={
            "preset": "daylight",
            "style": style,
            "mode": "interior",
            "room_type": room_type,
        },
    )


def test_interior_upload_creates_job_with_mode(client: TestClient) -> None:
    resp = _upload_interior(client, _png_bytes())
    assert resp.status_code == 201
    body = resp.json()
    assert body["mode"] == "interior"
    assert body["room_type"] == "bedroom"
    # Detail + list surface the mode too.
    detail = client.get(f"/api/v1/renders/{body['id']}").json()
    assert detail["mode"] == "interior"
    assert detail["room_type"] == "bedroom"
    items = client.get("/api/v1/renders").json()["items"]
    assert items[0]["mode"] == "interior"


def test_interior_default_room_type_is_living(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/renders",
        files={"file": ("room.png", _png_bytes(), "application/octet-stream")},
        data={"preset": "daylight", "style": "modern", "mode": "interior"},
    )
    assert resp.status_code == 201
    assert resp.json()["room_type"] == "living"


def test_interior_exterior_style_rejected(client: TestClient) -> None:
    # "warm" is an exterior-only style.
    resp = _upload_interior(client, _png_bytes(), style="warm")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_STYLE"


def test_interior_bad_room_type_rejected(client: TestClient) -> None:
    resp = _upload_interior(client, _png_bytes(), room_type="garage")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_ROOM_TYPE"


def test_bad_mode_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/renders",
        files={"file": ("x.png", _png_bytes(), "application/octet-stream")},
        data={"preset": "daylight", "style": "modern", "mode": "aerial"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_MODE"


def test_interior_generate_passes_mode_to_adapter(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    from app.adapters.openrouter import OpenRouterRenderAdapter

    captured: dict = {}

    def fake_generate(self, *a, **k):
        captured.update(k)
        return _png_bytes(400, 300)

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(OpenRouterRenderAdapter, "generate", fake_generate)
    job_id = _upload_interior(client, _png_bytes()).json()["id"]
    resp = client.post(f"/api/v1/renders/{job_id}/generate")
    assert resp.status_code == 202
    body = {}
    for _ in range(100):
        body = client.get(f"/api/v1/renders/{job_id}").json()
        if body["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert body["status"] == "succeeded"
    assert captured.get("mode") == "interior"
    assert captured.get("room_type") == "bedroom"


def test_interior_prompt_keeps_structure() -> None:
    from app.adapters.gemini import interior_prompt

    text = interior_prompt("kitchen", "luxury", "daylight")
    assert "kitchen" in text
    assert "exactly unchanged" in text
    assert "marble" in text  # luxury direction


def test_interior_bd_room_types_accepted(client: TestClient) -> None:
    for rt in ("drawing", "master_bedroom", "child_bedroom", "bathroom"):
        resp = _upload_interior(client, _png_bytes(), room_type=rt)
        assert resp.status_code == 201, rt
        assert resp.json()["room_type"] == rt


def test_interior_prompt_under_construction() -> None:
    from app.adapters.gemini import interior_prompt

    text = interior_prompt("bathroom", "modern", "daylight")
    assert "UNDER-CONSTRUCTION" in text
    assert "commode" in text  # bathroom program
    text = interior_prompt("master_bedroom", "modern", "daylight")
    assert "master bedroom" in text
    assert "king-size bed" in text
    text = interior_prompt("child_bedroom", "modern", "daylight")
    assert "study desk" in text
