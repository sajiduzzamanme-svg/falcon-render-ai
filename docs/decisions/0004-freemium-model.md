# ADR 0004 — Freemium model (2026-10-18)

## Decision (Mavi, 2026-10-18)
- **Anonymous (no login):** can render (1 free trial per device/IP hash),
  **cannot download**. Watermarked preview only. Anonymous-created jobs
  (`user_id` NULL) are **never downloadable by anyone** — not even by a
  signed-in user who knows the job id.
- **Signed-up free user:** renders AND downloads within their free credits;
  beyond that the generate endpoint returns **402 INSUFFICIENT_CREDITS**
  and the UI points at the pricing page — they must buy a package.
- **Every new user gets 30 free credits on signup** (`signup_bonus` ledger
  entry, `reason='grant'`). 30 ÷ 10 = **3 renders with download**.
- **Download rule:** only the job's owner (`jobs.user_id`) may download
  the full-resolution render, via `/renders/{id}/download` (signed URL)
  or `/files/{id}/render`. Resolves the creator-only question from
  2026-10-18: tightened, no exceptions.
- **Preview** (`/files/{id}/preview`, watermarked, ≤900px) stays public —
  it is the anonymous user's whole product.

## What changes vs ADR 0003
- ADR 0003's free tier ("1 render free, no signup; signup required to
  download") is superseded: signup now grants 30 credits (≈3 renders),
  and anonymous jobs are no longer downloadable by signed-in users.
- Paid tiers unchanged: Starter 1000/$9.99, Growth 3000/$29.99,
  Studio 6000/$59.99; 1 render = 10 credits; failed renders never
  charged; credits never expire; fidelity retries free.

## Implementation notes
- Signup bonus lives in migration `0002_signup_bonus.sql`: `handle_new_user()`
  inserts the profile with `credits=30` and a `+30` ledger row
  (`reason='grant'`), idempotently (bonus only when the profile row is
  actually inserted — pre-migration users keep their existing balance).
- Backend: `credits.FREE_SIGNUP_CREDITS=30`; `_can_access_job` is
  owner-only; `owner_id` exposed on job detail so the frontend can set
  download-button state upfront; `GET /users/me` feeds the nav balance.
- Frontend: pricing page copy updated; nav shows a credit pill for
  signed-in users; download button states — anonymous → "Sign up to
  download", non-owner → disabled with explanation, 402 on generate →
  notice linking to /pricing.

## Status
Accepted 2026-10-18. Migration 0002 must be applied via the Supabase
dashboard SQL editor (PostgREST cannot run DDL).
