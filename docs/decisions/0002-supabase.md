# ADR 0002 — Supabase as the database (2026-10-18)

## Decision
Use **Supabase** as the database/backend platform for Falcon Render AI,
replacing the local JSON job store.

## Context
- Public launch needs: user accounts (signup-gated downloads), credit
  balances, persistent job history, artifact storage.
- Current state: thread-safe JSON files under `STORAGE_DIR` — fine for local
  dev, not for production.

## Why Supabase
- **Postgres:** `jobs`, `profiles`, `credit_ledger` tables; Row Level Security
  per user.
- **Auth:** email + OAuth (Google) out of the box — powers the
  "1 free render, signup to download" freemium gate.
- **Storage:** buckets for `sketches/`, `edges/`, `renders/` — replaces local
  `./storage`; serves watermarked previews + signed download URLs.

## Consequences
- Backend adds: Supabase client, RLS policies, credit deduction per
  generation (1 credit = 1 render attempt), anonymous trial tracking
  (1 free render per device/IP fingerprint — abuse-limited, not bulletproof).
- `STORAGE_DIR` JSON store stays as the local-dev fallback; production uses
  Supabase (env: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`).
- Fidelity retry loop must deduct per attempt — gate default stays 0.0 until
  calibrated, to avoid surprise credit burn.
- Migration order: tables + RLS → auth wiring → storage buckets → credit
  ledger → cut over job endpoints.

## Status
Accepted. Awaiting Supabase project credentials (via secure link, never chat).
