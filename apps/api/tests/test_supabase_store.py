"""Supabase job store + credits tests.

Two tiers:
- Unit tests use an in-memory fake client and always run. They cover the
  store interface, field mapping, and the full credit policy math
  (ADR 0003: 10 credits per completed render, failures never charged,
  1 anonymous free trial).
- Live tests hit the real Supabase project and are SKIPPED unless a working
  credential is available (``SUPABASE_URL``/``SUPABASE_SERVICE_KEY`` env vars,
  or the local connector surrogate). Live tests delete every row they
  create.
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

from app import credits, job_store, jobs_supabase
from app.config import settings
from app.supabase_client import SupabaseClient


# ---------------------------------------------------------------------------
# In-memory fake (duck-typed to SupabaseClient)
# ---------------------------------------------------------------------------
class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "jobs": [],
            "profiles": [],
            "credit_ledger": [],
            "anonymous_trials": [],
        }
        self._clock = 0

    def _now(self) -> str:
        self._clock += 1
        return f"2026-10-18T00:00:{self._clock:02d}+00:00"

    @staticmethod
    def _match(rows: list[dict], params: dict | None) -> list[dict]:
        out = list(rows)
        for key, value in (params or {}).items():
            if key in ("select", "order", "limit"):
                continue
            if isinstance(value, str) and value.startswith("eq."):
                out = [r for r in out if str(r.get(key)) == value[3:]]
        return out

    def select(self, table: str, params: dict | None = None) -> list[dict]:
        rows = self._match(self.tables[table], params)
        if (params or {}).get("order", "").startswith("created_at.desc"):
            rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return [dict(r) for r in rows]

    def insert(
        self, table: str, payload: dict, prefer: str = "return=representation"
    ) -> list[dict]:
        if (
            table == "anonymous_trials"
            and "ignore-duplicates" in (prefer or "")
            and any(
                r.get("id_hash") == payload.get("id_hash") for r in self.tables[table]
            )
        ):
            return []
        row = dict(payload)
        if table == "jobs" and "created_at" not in row:
            row["created_at"] = self._now()
        if table == "jobs":
            # Mimic DB column defaults.
            row.setdefault("fidelity_attempts", 0)
            row.setdefault("credits_charged", 0)
        self.tables[table].append(row)
        return [dict(row)]

    def update(
        self, table: str, values: dict, params: dict | None = None
    ) -> list[dict]:
        matched = self._match(self.tables[table], params)
        for row in matched:
            row.update(values)
        return [dict(r) for r in matched]

    def delete(self, table: str, params: dict | None = None) -> list[dict]:
        matched = self._match(self.tables[table], params)
        self.tables[table] = [r for r in self.tables[table] if r not in matched]
        return []


@pytest.fixture()
def fake() -> FakeSupabaseClient:
    return FakeSupabaseClient()


def _no_supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")


# ---------------------------------------------------------------------------
# Store selection
# ---------------------------------------------------------------------------
def test_store_selection_json_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_supabase_env(monkeypatch)
    from app import jobs as json_jobs

    assert job_store.get_store() is json_jobs


def test_store_selection_supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "x")
    assert job_store.get_store() is jobs_supabase


def test_proxy_delegates_to_selected_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _no_supabase_env(monkeypatch)
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    record = job_store.jobs.create(preset="daylight", style="modern")
    assert record["status"] == "queued"
    assert job_store.jobs.get(record["id"])["id"] == record["id"]


# ---------------------------------------------------------------------------
# Job store CRUD (fake)
# ---------------------------------------------------------------------------
def test_supabase_crud_roundtrip(fake: FakeSupabaseClient) -> None:
    record = jobs_supabase.create(preset="dusk", style="warm", client=fake)
    assert record["status"] == "queued"
    assert record["preset"] == "dusk"
    assert record["fidelity_attempts"] == 0

    fetched = jobs_supabase.get(record["id"], client=fake)
    assert fetched is not None and fetched["id"] == record["id"]

    updated = jobs_supabase.update(
        record["id"], client=fake, status="processing", fidelity_attempts=2
    )
    assert updated is not None
    assert updated["status"] == "processing"
    assert updated["fidelity_attempts"] == 2

    listed = jobs_supabase.list_jobs(client=fake)
    assert [j["id"] for j in listed] == [record["id"]]

    assert jobs_supabase.get("no-such-id", client=fake) is None
    assert jobs_supabase.update("no-such-id", client=fake, status="x") is None


def test_lighting_preset_mapping(fake: FakeSupabaseClient) -> None:
    record = jobs_supabase.create(preset="night", style="minimalist", client=fake)
    db_row = fake.tables["jobs"][0]
    assert db_row["lighting"] == "night"  # DB column is `lighting`
    assert "preset" not in db_row
    assert record["preset"] == "night"  # app record uses `preset`


def test_error_dict_serialization(fake: FakeSupabaseClient) -> None:
    record = jobs_supabase.create(preset="daylight", style="modern", client=fake)
    jobs_supabase.set_error(record["id"], "RENDER_FAILED", "boom", client=fake)
    fetched = jobs_supabase.get(record["id"], client=fake)
    assert fetched is not None
    assert fetched["status"] == "failed"
    assert fetched["error"] == {"code": "RENDER_FAILED", "message": "boom"}
    assert isinstance(fake.tables["jobs"][0]["error"], str)  # stored as TEXT


def test_list_order_newest_first(fake: FakeSupabaseClient) -> None:
    first = jobs_supabase.create(preset="daylight", style="modern", client=fake)
    second = jobs_supabase.create(preset="dusk", style="warm", client=fake)
    ids = [j["id"] for j in jobs_supabase.list_jobs(client=fake)]
    assert ids == [second["id"], first["id"]]


# ---------------------------------------------------------------------------
# Credits policy (fake) — ADR 0003
# ---------------------------------------------------------------------------
def _profile(fake: FakeSupabaseClient, user_id: str, credits: int) -> None:
    fake.tables["profiles"].append(
        {
            "id": user_id,
            "email": "u@example.com",
            "credits": credits,
            "free_render_used": False,
            "created_at": "2026-10-18T00:00:00+00:00",
        }
    )


def test_charge_success_deducts_10(fake: FakeSupabaseClient) -> None:
    user_id = str(uuid.uuid4())
    _profile(fake, user_id, 100)
    job = jobs_supabase.create(
        preset="daylight", style="modern", user_id=user_id, client=fake
    )

    credits.settle_job(job_id=job["id"], succeeded=True, user_id=user_id, client=fake)

    assert fake.tables["profiles"][0]["credits"] == 90
    ledger = fake.tables["credit_ledger"]
    assert len(ledger) == 1
    assert ledger[0]["delta"] == -10
    assert ledger[0]["reason"] == "render"
    assert ledger[0]["job_id"] == job["id"]
    assert ledger[0]["user_id"] == user_id
    assert fake.tables["jobs"][0]["credits_charged"] == 10


def test_failed_render_never_charged(fake: FakeSupabaseClient) -> None:
    user_id = str(uuid.uuid4())
    _profile(fake, user_id, 100)
    job = jobs_supabase.create(
        preset="daylight", style="modern", user_id=user_id, client=fake
    )

    credits.settle_job(job_id=job["id"], succeeded=False, user_id=user_id, client=fake)

    assert fake.tables["profiles"][0]["credits"] == 100
    assert fake.tables["credit_ledger"] == []
    assert fake.tables["jobs"][0]["credits_charged"] == 0


def test_insufficient_credits_blocks_generate(fake: FakeSupabaseClient) -> None:
    user_id = str(uuid.uuid4())
    _profile(fake, user_id, 5)
    with pytest.raises(credits.InsufficientCredits):
        credits.ensure_can_generate(user_id=user_id, client=fake)
    _profile(fake, str(uuid.uuid4()), 10)
    # exactly 10 is enough
    credits.ensure_can_generate(user_id=fake.tables["profiles"][1]["id"], client=fake)


def test_anonymous_trial_flow(fake: FakeSupabaseClient) -> None:
    h = "abc123hash"
    assert not credits.trial_used(client_hash=h, client=fake)
    credits.ensure_can_generate(client_hash=h, client=fake)  # no raise

    job = jobs_supabase.create(preset="daylight", style="modern", client=fake)
    credits.settle_job(job_id=job["id"], succeeded=True, client_hash=h, client=fake)

    assert credits.trial_used(client_hash=h, client=fake)
    with pytest.raises(credits.FreeTrialExhausted):
        credits.ensure_can_generate(client_hash=h, client=fake)


def test_failed_anonymous_render_does_not_burn_trial(
    fake: FakeSupabaseClient,
) -> None:
    h = "def456hash"
    job = jobs_supabase.create(preset="daylight", style="modern", client=fake)
    credits.settle_job(job_id=job["id"], succeeded=False, client_hash=h, client=fake)
    assert not credits.trial_used(client_hash=h, client=fake)


def test_credits_noop_without_supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_supabase_env(monkeypatch)
    # Must not raise and must not touch anything (local-dev fallback).
    credits.ensure_can_generate(user_id="u", client_hash="h")
    credits.settle_job(job_id="j", succeeded=True, user_id="u", client_hash="h")
    assert credits.get_balance(user_id="u") is None
    assert not credits.trial_used(client_hash="h")


# ---------------------------------------------------------------------------
# Live tests (skipped without a working credential)
# ---------------------------------------------------------------------------
def _live_client() -> SupabaseClient | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key:
        return SupabaseClient(url, key)
    # Dev convenience: the connector's surrogate (never the raw key). The
    # surrogate is swapped for the real key at approved egress.
    try:
        sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
        from dynamic_credentials import dynamic_credential_entry

        surrogate = dynamic_credential_entry("custom.supabase")["surrogate"]
    except Exception:  # noqa: BLE001 — any failure means "no live credential"
        return None
    return SupabaseClient("https://pzdtgkgfsleyafhqvujd.supabase.co", surrogate)


@pytest.fixture()
def live() -> SupabaseClient:
    client = _live_client()
    if client is None:
        pytest.skip("live Supabase not available")
    try:
        client.select("jobs", params={"select": "id", "limit": "1"})
    except Exception as exc:  # noqa: BLE001 — any failure means "unreachable"
        pytest.skip(f"live Supabase unreachable: {exc}")
    return client


def test_live_crud_roundtrip(live: SupabaseClient) -> None:
    job_id: str | None = None
    try:
        record = jobs_supabase.create(preset="dusk", style="warm", client=live)
        job_id = record["id"]
        assert record["status"] == "queued"
        assert record["preset"] == "dusk"

        fetched = jobs_supabase.get(job_id, client=live)
        assert fetched is not None and fetched["id"] == job_id

        updated = jobs_supabase.update(
            job_id, client=live, status="processing", fidelity_attempts=1
        )
        assert updated is not None and updated["status"] == "processing"

        ids = [j["id"] for j in jobs_supabase.list_jobs(client=live)]
        assert job_id in ids
    finally:
        if job_id:
            live.delete("jobs", params={"id": f"eq.{job_id}"})
    assert jobs_supabase.get(job_id, client=live) is None


def test_live_anonymous_trial(live: SupabaseClient) -> None:
    h = f"test-{uuid.uuid4().hex[:12]}"
    try:
        assert not credits.trial_used(client_hash=h, client=live)
        live.insert("anonymous_trials", {"id_hash": h}, prefer=None)
        assert credits.trial_used(client_hash=h, client=live)
    finally:
        live.delete("anonymous_trials", params={"id_hash": f"eq.{h}"})
    assert not credits.trial_used(client_hash=h, client=live)
