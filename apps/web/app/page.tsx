import Link from "next/link";
import CompareSlider from "./components/compare-slider";

const STEPS = [
  {
    n: "1",
    title: "Upload your sketch",
    text: "Drop a 3D model view, floor plan, or massing. Add a style reference for materials and mood — optional.",
  },
  {
    n: "2",
    title: "Choose the look",
    text: "Pick lighting (Daylight, Dusk, Night) and style (Modern, Minimalist, Warm) on visual cards.",
  },
  {
    n: "3",
    title: "Generate & download",
    text: "Get a photorealistic render locked to your geometry, with a fidelity score proving it.",
  },
];

const EXAMPLES = [
  {
    src: "/demo/render.webp",
    alt: "Twin residential towers rendered in red brick",
    caption: "Sketch → brick residential towers",
  },
  {
    src: "/demo/ex1.webp",
    alt: "Three-storey apartment building in daylight",
    caption: "Massing model → daylight render",
  },
  {
    src: "/demo/ex2.webp",
    alt: "Apartment building at dusk with warm interior lights",
    caption: "Same design → dusk mood",
  },
];

const PLANS = [
  { name: "Starter", price: "$9.99", detail: "1,000 credits · 100 renders" },
  { name: "Growth", price: "$29.99", detail: "3,000 credits · 300 renders" },
  { name: "Studio", price: "$59.99", detail: "6,000 credits · 600 renders" },
];

export default function LandingPage() {
  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <p className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-blue-800">
            Geometry-locked rendering
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
            Renders that never re-imagine your design
          </h1>
          <p className="mt-4 text-lg text-slate-600">
            Upload your sketch. Falcon Render AI extracts its geometry lock and
            renders it photorealistically —{" "}
            <strong className="font-semibold text-slate-900">
              walls, windows, and massing stay exactly where you put them.
            </strong>
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/studio"
              className="rounded-lg bg-blue-600 px-7 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Try 1 render free
            </Link>
            <Link
              href="/pricing"
              className="rounded-lg border border-slate-300 bg-white px-7 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              See pricing
            </Link>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            No signup needed to preview · 1 render = 10 credits
          </p>
        </div>
        <div>
          <CompareSlider
            beforeSrc="/demo/sketch.jpg"
            afterSrc="/demo/render.webp"
            beforeLabel="Your sketch"
            afterLabel="Falcon render"
          />
          <p className="mt-2 text-center text-xs text-slate-500">
            Drag the handle — same geometry, photorealistic finish
          </p>
        </div>
      </section>

      {/* How it works */}
      <section aria-label="How it works">
        <h2 className="text-center text-2xl font-bold tracking-tight">
          From sketch to render in three steps
        </h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <div
              key={s.n}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                {s.n}
              </span>
              <h3 className="mt-3 font-semibold">{s.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Examples */}
      <section aria-label="Example renders">
        <div className="flex items-end justify-between">
          <h2 className="text-2xl font-bold tracking-tight">
            Real sketches, real renders
          </h2>
          <Link
            href="/renders"
            className="text-sm font-semibold text-blue-700 hover:underline"
          >
            Open gallery →
          </Link>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {EXAMPLES.map((ex) => (
            <figure
              key={ex.src}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              <img
                src={ex.src}
                alt={ex.alt}
                loading="lazy"
                className="aspect-[4/3] w-full object-cover"
              />
              <figcaption className="px-4 py-3 text-sm text-slate-600">
                {ex.caption}
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      {/* Pricing teaser */}
      <section
        aria-label="Pricing"
        className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm"
      >
        <h2 className="text-2xl font-bold tracking-tight">
          Simple credit pricing
        </h2>
        <p className="mt-1 text-slate-600">
          1 render = 10 credits · credits never expire
        </p>
        <div className="mx-auto mt-6 grid max-w-2xl gap-4 sm:grid-cols-3">
          {PLANS.map((p) => (
            <div
              key={p.name}
              className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-5"
            >
              <p className="text-sm font-semibold text-slate-500">{p.name}</p>
              <p className="mt-1 text-2xl font-bold tabular-nums">{p.price}</p>
              <p className="mt-1 text-xs text-slate-500 tabular-nums">
                {p.detail}
              </p>
            </div>
          ))}
        </div>
        <Link
          href="/pricing"
          className="mt-6 inline-block rounded-lg bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2"
        >
          See full pricing
        </Link>
      </section>

      {/* Final CTA */}
      <section className="rounded-2xl bg-blue-600 px-8 py-12 text-center shadow-sm">
        <h2 className="text-2xl font-bold tracking-tight text-white">
          Your design deserves a faithful render
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-blue-100">
          Join architects who stopped fighting AI re-imagination. First render
          is free.
        </p>
        <Link
          href="/studio"
          className="mt-6 inline-block rounded-lg bg-white px-8 py-3 text-sm font-semibold text-blue-700 shadow hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
        >
          Start rendering free
        </Link>
      </section>
    </div>
  );
}
