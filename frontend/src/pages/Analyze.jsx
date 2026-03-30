import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { analyzeProperty } from '../services/analysisApi'

const initialForm = {
  borough: '',
  neighborhood: '',
  building_class: '',
  year_built: '',
  gross_sqft: '',
  land_sqft: '',
  latitude: '',
  longitude: '',
  market_price: '',
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value) {
  return `${value.toFixed(2)}%`
}

function getDealLabelStyles(label) {
  const normalized = label?.toLowerCase()

  if (normalized === 'buy') {
    return 'border-emerald-500/30 bg-emerald-500/15 text-emerald-300'
  }

  if (normalized === 'hold') {
    return 'border-amber-500/30 bg-amber-500/15 text-amber-300'
  }

  return 'border-rose-500/30 bg-rose-500/15 text-rose-300'
}

function StatCard({ label, value, tone = 'default' }) {
  const toneClasses =
    tone === 'positive'
      ? 'border-emerald-500/20 bg-emerald-500/10'
      : tone === 'negative'
        ? 'border-rose-500/20 bg-rose-500/10'
        : 'border-slate-800 bg-slate-950'

  return (
    <div className={`rounded-xl border p-4 ${toneClasses}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-xl font-bold text-white">{value}</p>
    </div>
  )
}

export default function Analyze() {
  const [formData, setFormData] = useState(initialForm)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  function handleChange(event) {
    const { name, value } = event.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  function buildPayload() {
    return {
      borough: formData.borough.trim(),
      neighborhood: formData.neighborhood.trim(),
      building_class: formData.building_class.trim(),
      year_built: Number(formData.year_built),
      gross_sqft: Number(formData.gross_sqft),
      land_sqft: Number(formData.land_sqft),
      latitude: Number(formData.latitude),
      longitude: Number(formData.longitude),
      market_price: Number(formData.market_price),
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setIsLoading(true)
    setError('')
    setAnalysisResult(null)

    try {
      const payload = buildPayload()
      const result = await analyzeProperty(payload)
      console.log('API result:', result)
      setAnalysisResult(result)
    } catch (err) {
      setError(err.message || 'Something went wrong while analyzing.')
    } finally {
      setIsLoading(false)
    }
  }

  const hasV2Result =
    analysisResult?.valuation &&
    analysisResult?.investment_analysis &&
    analysisResult?.drivers &&
    analysisResult?.explanation

  const dealLabel = analysisResult?.investment_analysis?.deal_label
  const score = analysisResult?.investment_analysis?.investment_score
  const difference = analysisResult?.valuation?.price_difference ?? 0

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-10 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
              PropIntel AI
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Property analysis workspace
            </h1>
            <p className="mt-3 max-w-2xl text-slate-300">
              Enter property details below to prepare an analysis request for
              the
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

        <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <h2 className="text-2xl font-semibold">Analysis Form</h2>
            <p className="mt-2 text-sm text-slate-400">
              Fill in the property inputs required by the v2 analysis contract.
            </p>

            <form onSubmit={handleSubmit} className="mt-6 space-y-6">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                  Property Basics
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="borough"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Borough
                    </label>
                    <input
                      id="borough"
                      name="borough"
                      type="text"
                      value={formData.borough}
                      onChange={handleChange}
                      placeholder="Brooklyn"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="neighborhood"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Neighborhood
                    </label>
                    <input
                      id="neighborhood"
                      name="neighborhood"
                      type="text"
                      value={formData.neighborhood}
                      onChange={handleChange}
                      placeholder="Park Slope"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label
                      htmlFor="building_class"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Building Class
                    </label>
                    <input
                      id="building_class"
                      name="building_class"
                      type="text"
                      value={formData.building_class}
                      onChange={handleChange}
                      placeholder="02 TWO FAMILY DWELLINGS"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="year_built"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Year Built
                    </label>
                    <input
                      id="year_built"
                      name="year_built"
                      type="number"
                      value={formData.year_built}
                      onChange={handleChange}
                      placeholder="1925"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                  Size & Location
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="gross_sqft"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Gross Sqft
                    </label>
                    <input
                      id="gross_sqft"
                      name="gross_sqft"
                      type="number"
                      value={formData.gross_sqft}
                      onChange={handleChange}
                      placeholder="1800"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="land_sqft"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Land Sqft
                    </label>
                    <input
                      id="land_sqft"
                      name="land_sqft"
                      type="number"
                      value={formData.land_sqft}
                      onChange={handleChange}
                      placeholder="2000"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="latitude"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Latitude
                    </label>
                    <input
                      id="latitude"
                      name="latitude"
                      type="number"
                      step="any"
                      value={formData.latitude}
                      onChange={handleChange}
                      placeholder="40.6720"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="longitude"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Longitude
                    </label>
                    <input
                      id="longitude"
                      name="longitude"
                      type="number"
                      step="any"
                      value={formData.longitude}
                      onChange={handleChange}
                      placeholder="-73.9778"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                  Pricing
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="market_price"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Market Price
                    </label>
                    <input
                      id="market_price"
                      name="market_price"
                      type="number"
                      value={formData.market_price}
                      onChange={handleChange}
                      placeholder="1250000"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isLoading ? 'Running Analysis...' : 'Run Analysis'}
              </button>

              {error ? (
                <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              ) : null}
            </form>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold">Analysis Results</h2>
                <p className="mt-2 text-sm text-slate-400">
                  Real backend results appear here after the analysis request
                  completes.
                </p>
              </div>

              {hasV2Result ? (
                <span
                  className={`inline-flex w-fit rounded-full border px-3 py-1 text-sm font-semibold ${getDealLabelStyles(
                    dealLabel
                  )}`}
                >
                  {dealLabel}
                </span>
              ) : null}
            </div>

            {!analysisResult && !isLoading ? (
              <div className="mt-6 rounded-xl border border-dashed border-slate-700 p-6 text-sm text-slate-500">
                Submit the form to fetch valuation, investment score, drivers,
                and explanation from the v2 backend.
              </div>
            ) : null}

            {isLoading ? (
              <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-sm text-slate-400">
                Loading analysis...
              </div>
            ) : null}

            {analysisResult && !hasV2Result && !isLoading ? (
              <div className="mt-6 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-200">
                The API returned a response, but it did not match the expected
                v2 grouped shape. Open the browser console and inspect
                <span className="mx-1 font-semibold text-white">
                  API result:
                </span>
                to verify what the backend returned.
              </div>
            ) : null}

            {hasV2Result ? (
              <div className="mt-6 space-y-6">
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <StatCard
                    label="Predicted Value"
                    value={formatCurrency(
                      analysisResult.valuation.predicted_price
                    )}
                  />
                  <StatCard
                    label="Market Price"
                    value={formatCurrency(analysisResult.valuation.market_price)}
                  />
                  <StatCard
                    label="Price Difference"
                    value={formatCurrency(
                      analysisResult.valuation.price_difference
                    )}
                    tone={difference >= 0 ? 'positive' : 'negative'}
                  />
                  <StatCard
                    label="Difference %"
                    value={formatPercent(
                      analysisResult.valuation.price_difference_pct
                    )}
                    tone={
                      analysisResult.valuation.price_difference_pct >= 0
                        ? 'positive'
                        : 'negative'
                    }
                  />
                </div>

                <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Investment Score
                    </p>
                    <p className="mt-4 text-5xl font-bold text-white">
                      {score}
                    </p>
                    <p className="mt-3 text-sm text-slate-400">
                      Confidence:{' '}
                      <span className="font-semibold text-white">
                        {analysisResult.investment_analysis.confidence}
                      </span>
                    </p>
                    <p className="mt-2 text-sm text-slate-400">
                      Recommendation:{' '}
                      <span className="font-semibold text-white">
                        {analysisResult.investment_analysis.recommendation}
                      </span>
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-cyan-400">
                      Investment Summary
                    </p>
                    <p className="mt-4 text-base leading-7 text-slate-200">
                      {analysisResult.investment_analysis.analysis_summary}
                    </p>

                    <div className="mt-5 grid gap-4 sm:grid-cols-2">
                      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                          ROI Estimate
                        </p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {formatPercent(
                            analysisResult.investment_analysis.roi_estimate
                          )}
                        </p>
                      </div>

                      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Model Version
                        </p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {analysisResult.metadata.model_version}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                      Top Drivers
                    </h3>
                    <ul className="mt-4 space-y-3 text-sm text-slate-300">
                      {analysisResult.drivers.top_drivers.map((driver) => (
                        <li
                          key={driver}
                          className="rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-3"
                        >
                          {driver}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                      Model Context
                    </h3>
                    <ul className="mt-4 space-y-3 text-sm text-slate-300">
                      {analysisResult.drivers.global_context.map((item) => (
                        <li
                          key={item}
                          className="rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-3"
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 animate-pulse text-amber-300 drop-shadow-[0_0_10px_rgba(252,211,77,0.35)]" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                      AI Explanation
                    </h3>
                  </div>

                  <div className="mt-4 grid gap-4 xl:grid-cols-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Summary
                      </p>
                      <p className="mt-3 text-sm leading-7 text-slate-300">
                        {analysisResult.explanation.summary}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Opportunity
                      </p>
                      <p className="mt-3 text-sm leading-7 text-slate-300">
                        {analysisResult.explanation.opportunity}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Risks
                      </p>
                      <p className="mt-3 text-sm leading-7 text-slate-300">
                        {analysisResult.explanation.risks}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  )
}