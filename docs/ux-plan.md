# Falcon Render AI — Public Frontend UX Plan (v0.2)

## Design principles (public easily use korte parbe)
1. **30-second rule:** notun user 30 second-e bujhbe ki korte hobe — kono tutorial lagbe na.
2. **2-click first render:** Upload → Generate — er beshi step na.
3. **Mobile-first:** beshirbhag user phone-e ashbe (WhatsApp/Facebook theke).
4. **Sketch = geometry, Reference = style:** ei separation UI-tei clear thakbe — user kokhono confuse hobe na konta ki kore.

## Page map (5 pages)
1. **Landing (`/`)** — Hero: before/after slider (sketch → render), 3-step "how it works",
   example gallery, pricing teaser, CTA "Try free". No signup wall.
2. **Studio (`/studio`)** — ashol kaj-er page (niche detail).
3. **Gallery (`/gallery`)** — public example renders + user-er nijer history (login thakle).
4. **Pricing (`/pricing`)** — credit packs; 1 free render trial.
5. **Dashboard (`/dashboard`)** — credit balance, render history, download again.

## Studio page flow (core UX)
**Step 1 — Upload (side by side, duita drop zone):**
- Left: "Your sketch" (required) — 3D model screenshot/floor plan/massing. Example thumbnail dekhabe.
- Right: "Style reference" (optional) — material/color/mood. Example thumbnail dekhabe.
- Niche ek line-e clear kora: "Geometry ashbe sketch theke, style ashbe reference theke."
- Upload-er sathe sathe edge-map preview ("geometry lock") dekhabe — trust build hoy.

**Step 2 — Presets (visual cards, dropdown na):**
- Lighting: Daylight / Dusk / Night — chobi-wala card.
- Style: Modern / Minimalist / Warm — chobi-wala card.
- Advanced (collapsible): strength slider, aspect ratio.

**Step 3 — Result:**
- Sketch vs render **compare slider** (drag kore dekhbe).
- **Fidelity badge** plain bhashay: "Design match: 92% — geometry preserved" (amber hole "check recommended").
- Button: Download, "Try another style" (same sketch), "New sketch".

## Public-friendly details
- **Free trial:** signup charai 1-ta free render — full preview dekhbe (watermarked),
  kintu **download korte gele signup lagbe**. "Sign up to download" CTA.
- **Credit meter:** header-e sobsomoy balance dekhabe ("12 credits left").
- **Progress:** generate-er somoy live status ("Rendering… preserving geometry"), 30-60s expectation set kora.
- **Empty/error states:** honest message, kokhono fake render na (existing 503 pattern).
- **Language:** English default + Bangla toggle (BD market-er jonno).
- **Share:** result page-er shareable link (watermarked free tier) — organic growth.

## What changes from current v0.1 UI
- Add: reference image upload zone + landing/pricing/dashboard pages.
- Change: preset dropdown → visual cards; fidelity score → plain-language badge + compare slider.
- Keep: 3-panel job view (sketch/edge/render), honest 503/failed states, no dead buttons.

## Build order (after approval)
1. Supabase wiring (tables + RLS + Auth + Storage buckets) — see `docs/decisions/0002-supabase.md`.
2. Studio page rebuild (upload + reference + cards + compare slider), signup-gated download.
3. Landing page.
4. Pricing + credit ledger.
5. Dashboard.
