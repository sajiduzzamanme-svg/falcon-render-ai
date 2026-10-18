"""Freemium model tests (ADR 0004).

- Signup bonus constants: 30 free credits = 3 renders.
- Migration 0002 SQL parses (pglast — validates the outer SQL; the
  plpgsql body is a string to the parser, so body internals are checked
  by text assertions + the documented apply run).
- GET /users/me: 401 anonymous, 200 with id/email/credits for authed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import credits
from app.auth import get_current_user, get_optional_user
from app.config import settings
from app.main import app

MIGRATION_0002 = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "0002_signup_bonus.sql"
)


def test_signup_bonus_is_30_credits() -> None:
    assert credits.FREE_SIGNUP_CREDITS == 30


def test_signup_bonus_covers_3_renders() -> None:
    # Mavi-confirmed: 30 credits / 10 per render = 3 renders with download.
    assert credits.FREE_SIGNUP_CREDITS // credits.CREDITS_PER_RENDER == 3


def test_migration_0002_parses() -> None:
    """pglast (libpg_query) must accept the migration file."""
    pglast = pytest.importorskip("pglast")
    sql = MIGRATION_0002.read_text(encoding="utf-8")
    stmts = pglast.parse_sql(sql)
    assert len(stmts) == 1  # one CREATE OR REPLACE FUNCTION


def test_migration_0002_grants_bonus() -> None:
    """Text-level checks on the parts pglast cannot see (plpgsql body)."""
    sql = MIGRATION_0002.read_text(encoding="utf-8")
    assert "handle_new_user" in sql
    assert "credits" in sql
    assert ", 30)" in sql  # values (new.id, new.email, 30)
    assert "'grant'" in sql  # allowed by the 0001 reason check constraint
    # Idempotent: bonus only when the profile row is actually inserted.
    assert "on conflict (id) do nothing" in sql
    assert "if found then" in sql


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")
    return TestClient(app)


@pytest.fixture()
def _clean_overrides(client: TestClient):
    yield
    client.app.dependency_overrides.clear()


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


def test_users_me_anonymous_401(client: TestClient) -> None:
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_users_me_authed(client: TestClient, _clean_overrides) -> None:
    _authed(client, user_id="user-abc")
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "user-abc"
    assert body["email"] == "a@b.c"
    # JSON fallback mode (no Supabase): no profile store → credits null.
    assert body["credits"] is None
