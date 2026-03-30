import { useState } from 'react'
import { Link } from 'react-router-dom'
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

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Analysis Form</h2>
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
            <h2 className="text-xl font-semibold">Analysis Results</h2>
            <p className="mt-2 text-sm text-slate-400">
              Real backend results will appear here after the analysis request
              completes.
            </p>

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
              <div className="mt-6 space-y-4">
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                    Valuation
                  </h3>
                  <div className="mt-3 space-y-2 text-sm text-slate-300">
                    <p>
                      <span className="font-semibold text-white">
                        Predicted Price:
                      </span>{' '}
                      $
                      {analysisResult.valuation.predicted_price.toLocaleString()}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Market Price:
                      </span>{' '}
                      ${analysisResult.valuation.market_price.toLocaleString()}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Difference:
                      </span>{' '}
                      $
                      {analysisResult.valuation.price_difference.toLocaleString()}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Difference %:
                      </span>{' '}
                      {analysisResult.valuation.price_difference_pct.toFixed(2)}
                      %
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                    Investment Analysis
                  </h3>
                  <div className="mt-3 space-y-2 text-sm text-slate-300">
                    <p>
                      <span className="font-semibold text-white">Score:</span>{' '}
                      {analysisResult.investment_analysis.investment_score}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Deal Label:
                      </span>{' '}
                      {analysisResult.investment_analysis.deal_label}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Recommendation:
                      </span>{' '}
                      {analysisResult.investment_analysis.recommendation}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Confidence:
                      </span>{' '}
                      {analysisResult.investment_analysis.confidence}
                    </p>
                    <p>
                      <span className="font-semibold text-white">Summary:</span>{' '}
                      {analysisResult.investment_analysis.analysis_summary}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                    Top Drivers
                  </h3>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-300">
                    {analysisResult.drivers.top_drivers.map((driver) => (
                      <li key={driver}>{driver}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                    Explanation
                  </h3>
                  <div className="mt-3 space-y-3 text-sm text-slate-300">
                    <p>
                      <span className="font-semibold text-white">Summary:</span>{' '}
                      {analysisResult.explanation.summary}
                    </p>
                    <p>
                      <span className="font-semibold text-white">
                        Opportunity:
                      </span>{' '}
                      {analysisResult.explanation.opportunity}
                    </p>
                    <p>
                      <span className="font-semibold text-white">Risks:</span>{' '}
                      {analysisResult.explanation.risks}
                    </p>
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