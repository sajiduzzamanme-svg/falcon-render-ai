import Link from "next/link";

const TIERS = [
  {
    name: "Starter",
    credits: "1,000",
    price: "$9.99",
    renders: "100 renders",
    tagline: "For trying out client work",
    featured: false,
  },
  {
    name: "Growth",
    credits: "3,000",
    price: "$29.99",
    renders: "300 renders",
    tagline: "For regular project flow",
    featured: true,
  },
  {
    name: "Studio",
    credits: "6,000",
    price: "$59.99",
    renders: "600 renders",
    tagline: "For teams and heavy use",
    featured: false,
  },
];

const INCLUDED = [
  "All lighting presets (Daylight, Dusk, Night)",
  "Style reference upload",
  "Geometry lock + fidelity score on every render",
  "Commercial use of renders",
  "Credits never expire",
];

export default function PricingPage() {
  return (
    <div className="space-y-10">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">
          Simple credit pricing
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-slate-600">
          <strong className="font-semibold text-slate-900">
            1 render = 10 credits.
          </strong>{" "}
          Pay for renders, nothing else. Same rate on every pack — no tricks.
        </p>
      </div>

      <div className="mx-auto flex max-w-2xl items-center justify-between gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-6 py-4">
        <div>
          <p className="text-sm font-semibold text-emerald-900">
            Start free — no signup needed
          </p>
          <p className="text-xs text-emerald-700">
            Render 1 sketch and see a watermarked preview. Sign up to
            download — new accounts get{" "}
            <strong className="font-semibold">30 free credits</strong> (≈3
            full renders with download).
          </p>
        </div>
        <Link
          href="/"
          className="shrink-0 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
        >
          Try free
        </Link>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {TIERS.map((tier) => (
          <div
            key={tier.name}
            className={`relative flex flex-col rounded-2xl border bg-white p-6 shadow-sm ${
              tier.featured
                ? "border-blue-600 ring-2 ring-blue-600/20"
                : "border-slate-200"
            }`}
          >
            {tier.featured && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
                Most popular
              </span>
            )}
            <h2 className="text-lg font-bold">{tier.name}</h2>
            <p className="mt-1 text-sm text-slate-500">{tier.tagline}</p>
            <p className="mt-4">
              <span className="text-4xl font-bold tracking-tight">
                {tier.price}
              </span>
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900 tabular-nums">
              {tier.credits} credits
            </p>
            <p className="text-sm text-slate-500 tabular-nums">
              ≈ {tier.renders} · $0.10 per render
            </p>
            <ul className="mt-6 flex-1 space-y-2.5">
              {INCLUDED.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2 text-sm text-slate-600"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    aria-hidden="true"
                    className="mt-0.5 shrink-0 text-emerald-600"
                  >
                    <path
                      d="M3 8.5 6.5 12 13 4.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
            <button
              type="button"
              disabled
              title="Checkout launches with Supabase Auth + payments"
              className="mt-6 cursor-not-allowed rounded-lg bg-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-500"
            >
              Checkout coming soon
            </button>
          </div>
        ))}
      </div>

      <section
        aria-label="How credits work"
        className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h2 className="text-lg font-semibold">How credits work</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600">
          <li>
            New accounts start with{" "}
            <strong className="font-semibold text-slate-900">
              30 free credits
            </strong>{" "}
            (≈3 renders) — no card required.
          </li>
          <li>
            Without an account you can render once and see a watermarked
            preview; downloads always require a free account.
          </li>
          <li>
            Every completed render costs{" "}
            <strong className="font-semibold text-slate-900">10 credits</strong>,
            regardless of preset or style.
          </li>
          <li>
            Failed renders are never charged — you only pay when a render
            succeeds.
          </li>
          <li>
            Credits never expire. Buy a pack once, use it whenever.
          </li>
          <li>
            Fidelity retries are included: if a render scores below your
            threshold, the retry is on us.
          </li>
        </ul>
      </section>
    </div>
  );
}
