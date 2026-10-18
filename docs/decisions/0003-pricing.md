# ADR 0003 — Credit pricing model (2026-10-18)

## Decision
- **1 completed render = 10 credits**, regardless of preset/style.
- Tiers (linear, same per-credit rate ≈ $0.01):
  - Starter: 1,000 credits = **$9.99** (≈100 renders)
  - Growth: 3,000 credits = **$29.99** (≈300 renders) — most popular
  - Studio: 6,000 credits = **$59.99** (≈600 renders)
- Free tier: 1 render free, no signup; signup required to download.
- Failed renders are never charged. Credits never expire.
- Fidelity-gate retries are included at no extra charge (gate defaults OFF,
  so no surprise cost; worst case 3 attempts ≈ $0.12 vs $0.10 revenue — rare
  and user-opted-in).

## Unit economics (sanity check)
- Provider cost per render ≈ $0.035–0.05 (Nano Banana via OpenRouter).
- Revenue per render = $0.10 → gross margin ≈ 50–65% before infra.
- Healthy headroom for Supabase + hosting + payment fees.

## Status
Accepted. Pricing page built (`/pricing`); checkout + ledger ship with
Supabase Auth + payments.
