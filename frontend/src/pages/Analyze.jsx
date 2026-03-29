import { Link } from 'react-router-dom'

export default function Analyze() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-10 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
              PropIntel AI
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Property analysis workspace
            </h1>
            <p className="mt-3 max-w-2xl text-slate-300">
              This page will power the first frontend MVP workflow using the
              <span className="mx-1 font-semibold text-white">
                /analyze-property-v2
              </span>
              endpoint.
            </p>
          </div>

          <Link
            to="/"
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:border-slate-500 hover:bg-slate-900"
          >
            Back Home
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Analysis Form</h2>
            <p className="mt-2 text-sm text-slate-400">
              Next step: build the property input form here.
            </p>

            <div className="mt-6 rounded-xl border border-dashed border-slate-700 p-6 text-sm text-slate-500">
              Form fields for borough, neighborhood, building class, year built,
              square footage, coordinates, and market price will live here.
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Analysis Results</h2>
            <p className="mt-2 text-sm text-slate-400">
              Next step: render valuation, investment score, drivers, and AI
              explanation here.
            </p>

            <div className="mt-6 rounded-xl border border-dashed border-slate-700 p-6 text-sm text-slate-500">
              Result cards powered by the v2 backend response will appear here
              after we connect the API.
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}