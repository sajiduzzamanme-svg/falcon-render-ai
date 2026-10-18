"""Credit ledger + anonymous free trial (ADR 0003).

Pricing: 1 completed render = 10 credits. Failed renders are never charged.
Fidelity-gate retries inside one render are free (ADR 0003: "retries included
at no extra charge"); the single 10-credit charge lands when the render
succeeds. The anonymous free trial (1 render, no signup) is consumed on
success, so a failed free render does not burn the trial.

NOTE (spec tension, 2026-10-18): the wiring task text said "deduct 10
credits per render ATTEMPT (fidelity retry loop!)". Implemented per ADR
0003 instead — one charge per completed render, retries free — because
ADR 0003 is the accepted pricing decision. If per-attempt charging is
wanted, it is a one-function change in ``settle_job``.

All functions no-op when Supabase is not configured (JSON fallback =
local dev, renders are free).
"""

from __future__ import annotations

import logging

from .supabase_client import SupabaseClient, SupabaseError, get_client

logger = logging.getLogger(__name__)

CREDITS_PER_RENDER = 10

# Free credits granted to every new signup (ADR 0004).
# 30 credits = 3 full renders with download (30 / 10).
FREE_SIGNUP_CREDITS = 30

LEDGER_TABLE = "credit_ledger"
PROFILES_TABLE = "profiles"
TRIALS_TABLE = "anonymous_trials"
JOBS_TABLE = "jobs"


class InsufficientCredits(Exception):
    """User's credit balance is below the cost of one render."""


class FreeTrialExhausted(Exception):
    """Anonymous free trial already used; signup required to continue."""


def _resolve(client: SupabaseClient | None) -> SupabaseClient | None:
    return client if client is not None else get_client()


def get_balance(*, user_id: str, client: SupabaseClient | None = None) -> int | None:
    """Return the user's credit balance, or None if no profile / no client."""
    c = _resolve(client)
    if c is None or not user_id:
        return None
    rows = c.select(PROFILES_TABLE, params={"id": f"eq.{user_id}", "select": "credits"})
    return rows[0]["credits"] if rows else None


def trial_used(*, client_hash: str, client: SupabaseClient | None = None) -> bool:
    """True when this device/IP hash already consumed its free render."""
    c = _resolve(client)
    if c is None:
        return False
    rows = c.select(
        TRIALS_TABLE, params={"id_hash": f"eq.{client_hash}", "select": "id_hash"}
    )
    return bool(rows)


def ensure_can_generate(
    *,
    user_id: str | None = None,
    client_hash: str | None = None,
    client: SupabaseClient | None = None,
) -> None:
    """Raise before starting generation when the actor cannot pay.

    No-op when Supabase is not configured (local-dev fallback).
    """
    c = _resolve(client)
    if c is None:
        return
    if user_id:
        balance = get_balance(user_id=user_id, client=c)
        if balance is None or balance < CREDITS_PER_RENDER:
            raise InsufficientCredits(
                f"Need {CREDITS_PER_RENDER} credits for one render."
            )
    elif client_hash and trial_used(client_hash=client_hash, client=c):
        raise FreeTrialExhausted(
            "Free trial already used. Signup is required to continue."
        )


def settle_job(
    *,
    job_id: str,
    succeeded: bool,
    user_id: str | None = None,
    client_hash: str | None = None,
    client: SupabaseClient | None = None,
) -> None:
    """Settle credits for a finished render attempt.

    - succeeded=True, authenticated user: deduct 10 credits, write the
      ledger entry (reason='render'), mark jobs.credits_charged.
    - succeeded=True, anonymous: consume the one free trial.
    - succeeded=False: no-op — failed renders are never charged (ADR 0003).
    - No Supabase configured: no-op (local-dev fallback).
    """
    c = _resolve(client)
    if c is None or not succeeded:
        return
    if user_id:
        _charge_user(c, job_id=job_id, user_id=user_id)
    elif client_hash:
        _consume_trial(c, client_hash=client_hash)


def _charge_user(client: SupabaseClient, *, job_id: str, user_id: str) -> None:
    rows = client.select(
        PROFILES_TABLE, params={"id": f"eq.{user_id}", "select": "credits"}
    )
    if not rows:
        raise SupabaseError(f"No profile row for user {user_id}")
    new_balance = rows[0]["credits"] - CREDITS_PER_RENDER
    client.update(PROFILES_TABLE, {"credits": new_balance}, {"id": f"eq.{user_id}"})
    client.insert(
        LEDGER_TABLE,
        {
            "user_id": user_id,
            "delta": -CREDITS_PER_RENDER,
            "reason": "render",
            "job_id": job_id,
        },
        prefer=None,
    )
    client.update(
        JOBS_TABLE, {"credits_charged": CREDITS_PER_RENDER}, {"id": f"eq.{job_id}"}
    )
    logger.info("Charged %d credits for job %s", CREDITS_PER_RENDER, job_id)


def _consume_trial(client: SupabaseClient, *, client_hash: str) -> None:
    client.insert(
        TRIALS_TABLE,
        {"id_hash": client_hash},
        prefer="resolution=ignore-duplicates",
    )
    logger.info("Consumed anonymous free trial for hash %.8s...", client_hash)
