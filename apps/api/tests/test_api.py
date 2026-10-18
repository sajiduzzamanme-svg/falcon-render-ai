"""API contract tests (TestClient). STORAGE_DIR is isolated per test."""

import io
from pathlib import Path

import pytest
from app import jobs
from app.config import settings
from app.main import app
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
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
    resp = client.get(f"/api/v1/files/{job_id}/render")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


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
