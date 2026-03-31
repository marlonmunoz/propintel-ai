import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { analyzeProperty } from '../services/analysisApi'
import Navbar from '../components/Navbar'

const boroughOptions = [
  'Bronx',
  'Brooklyn',
  'Manhattan',
  'Queens',
  'Staten Island',
]

const buildingClassOptions = [
  '01 ONE FAMILY DWELLINGS',
  '02 TWO FAMILY DWELLINGS',
  '03 THREE FAMILY DWELLINGS',
  '07 RENTALS - WALKUP APARTMENTS',
  '08 RENTALS - ELEVATOR APARTMENTS',
  '09 COOPS - WALKUP APARTMENTS',
  '10 COOPS - ELEVATOR APARTMENTS',
  '13 CONDOS - ELEVATOR APARTMENTS',
  '14 CONDOS - WALKUP APARTMENTS',
]

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

const samplePresets = {
  Brooklyn: {
    borough: 'Brooklyn',
    neighborhood: 'Park Slope',
    building_class: '02 TWO FAMILY DWELLINGS',
    year_built: '1925',
    gross_sqft: '1800',
    land_sqft: '2000',
    latitude: '40.6720',
    longitude: '-73.9778',
    market_price: '1250000',
  },
  Manhattan: {
    borough: 'Manhattan',
    neighborhood: 'Upper West Side',
    building_class: '13 CONDOS - ELEVATOR APARTMENTS',
    year_built: '1988',
    gross_sqft: '1100',
    land_sqft: '0',
    latitude: '40.7870',
    longitude: '-73.9754',
    market_price: '1850000',
  },
  Queens: {
    borough: 'Queens',
    neighborhood: 'Astoria',
    building_class: '01 ONE FAMILY DWELLINGS',
    year_built: '1940',
    gross_sqft: '1600',
    land_sqft: '2200',
    latitude: '40.7644',
    longitude: '-73.9235',
    market_price: '980000',
  },
  Bronx: {
    borough: 'Bronx',
    neighborhood: 'Riverdale',
    building_class: '01 ONE FAMILY DWELLINGS',
    year_built: '1935',
    gross_sqft: '2100',
    land_sqft: '3000',
    latitude: '40.9006',
    longitude: '-73.9067',
    market_price: '875000',
  },
  'Staten Island': {
    borough: 'Staten Island',
    neighborhood: 'Tottenville',
    building_class: '01 ONE FAMILY DWELLINGS',
    year_built: '1998',
    gross_sqft: '2400',
    land_sqft: '4200',
    latitude: '40.5084',
    longitude: '-74.2396',
    market_price: '825000',
  },
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

function getScoreCategory(score) {
  if (score >= 80) {
    return {
      label: 'Strong',
      classes: 'border-lime-500/30 bg-lime-500/15 text-lime-300',
    }
  }

  if (score >= 60) {
    return {
      label: 'Moderate',
      classes: 'border-cyan-500/30 bg-cyan-500/15 text-cyan-300',
    }
  }

  if (score >= 40) {
    return {
      label: 'Cautious',
      classes: 'border-amber-500/30 bg-amber-500/15 text-amber-300',
    }
  }

  return {
    label: 'Weak',
    classes: 'border-rose-500/30 bg-rose-500/15 text-rose-300',
  }
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

function FieldError({ message }) {
  if (!message) return null

  return <p className="mt-2 text-sm text-rose-300">{message}</p>
}

function getInputClasses(hasError) {
  return `w-full rounded-xl border bg-slate-950 px-4 py-3 text-white outline-none transition ${
    hasError
      ? 'border-rose-400 focus:border-rose-300'
      : 'border-slate-700 focus:border-cyan-400'
  }`
}

function validateForm(formData) {
  const errors = {}

  if (!formData.borough.trim()) {
    errors.borough = 'Borough is required.'
  }

  if (!formData.neighborhood.trim()) {
    errors.neighborhood = 'Neighborhood is required.'
  }

  if (!formData.building_class.trim()) {
    errors.building_class = 'Building class is required.'
  }

  const yearBuilt = Number(formData.year_built)
  if (!formData.year_built) {
    errors.year_built = 'Year built is required.'
  } else if (Number.isNaN(yearBuilt) || yearBuilt < 1800 || yearBuilt > 2026) {
    errors.year_built = 'Enter a valid year built between 1800 and 2026.'
  }

  const grossSqft = Number(formData.gross_sqft)
  if (!formData.gross_sqft) {
    errors.gross_sqft = 'Gross square footage is required.'
  } else if (Number.isNaN(grossSqft) || grossSqft <= 0) {
    errors.gross_sqft = 'Gross square footage must be greater than 0.'
  }

  const landSqft = Number(formData.land_sqft)
  if (!formData.land_sqft) {
    errors.land_sqft = 'Land square footage is required.'
  } else if (Number.isNaN(landSqft) || landSqft < 0) {
    errors.land_sqft = 'Land square footage must be 0 or greater.'
  }

  const latitude = Number(formData.latitude)
  if (!formData.latitude) {
    errors.latitude = 'Latitude is required.'
  } else if (Number.isNaN(latitude) || latitude < -90 || latitude > 90) {
    errors.latitude = 'Latitude must be between -90 and 90.'
  }

  const longitude = Number(formData.longitude)
  if (!formData.longitude) {
    errors.longitude = 'Longitude is required.'
  } else if (Number.isNaN(longitude) || longitude < -180 || longitude > 180) {
    errors.longitude = 'Longitude must be between -180 and 180.'
  }

  const marketPrice = Number(formData.market_price)
  if (!formData.market_price) {
    errors.market_price = 'Market price is required.'
  } else if (Number.isNaN(marketPrice) || marketPrice <= 0) {
    errors.market_price = 'Market price must be greater than 0.'
  }

  return errors
}

export default function Analyze() {
  const [formData, setFormData] = useState(initialForm)
  const [formErrors, setFormErrors] = useState({})
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  function handleChange(event) {
    const { name, value } = event.target

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))

    setFormErrors((prev) => {
      if (!prev[name]) return prev
      const next = { ...prev }
      delete next[name]
      return next
    })
  }

  function handleUsePreset(presetName) {
    const preset = samplePresets[presetName]
    if (!preset) return

    setFormData(preset)
    setFormErrors({})
    setError('')
    setAnalysisResult(null)
  }

  function handleResetForm() {
    setFormData(initialForm)
    setFormErrors({})
    setAnalysisResult(null)
    setError('')
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
    setError('')
    setAnalysisResult(null)

    const validationErrors = validateForm(formData)
    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors)
      return
    }

    setFormErrors({})
    setIsLoading(true)

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
  const scoreCategory = score !== undefined ? getScoreCategory(score) : null
  const difference = analysisResult?.valuation?.price_difference ?? 0

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <Navbar />
      <section className="mx-auto max-w-7xl px-6 pb-12 pt-24">
        <div className="mb-10 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
              PropIntel AI
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Property Analysis Workspace
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
            <div>
                <h2 className="text-2xl font-semibold">Analysis Form</h2>
                <p className="mt-2 text-sm text-slate-400">
                    Fill in the property inputs required by the v2 analysis contract.
                </p>
                <br />
                <p className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                    sample presets
                </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {Object.keys(samplePresets).map((presetName) => (
                  <button
                    key={presetName}
                    type="button"
                    onClick={() => handleUsePreset(presetName)}
                    className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-sm font-semibold text-cyan-300 transition hover:bg-cyan-500/20"
                  >
                    {presetName}
                  </button>
                ))}

                <button
                  type="button"
                  onClick={handleResetForm}
                  className="rounded-xl border border-slate-700 px-3 py-2 text-sm font-semibold text-white transition hover:border-slate-500 hover:bg-slate-900"
                >
                  Reset Form
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="mt-6 space-y-6" noValidate>
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
                    <select
                      id="borough"
                      name="borough"
                      value={formData.borough}
                      onChange={handleChange}
                      className={getInputClasses(!!formErrors.borough)}
                    >
                      <option value="" className="bg-slate-950 text-slate-400">
                        Select borough
                      </option>
                      {boroughOptions.map((borough) => (
                        <option
                          key={borough}
                          value={borough}
                          className="bg-slate-950 text-white"
                        >
                          {borough}
                        </option>
                      ))}
                    </select>
                    <FieldError message={formErrors.borough} />
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
                      className={getInputClasses(!!formErrors.neighborhood)}
                    />
                    <FieldError message={formErrors.neighborhood} />
                  </div>

                  <div className="sm:col-span-2">
                    <label
                      htmlFor="building_class"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Building Class
                    </label>
                    <select
                      id="building_class"
                      name="building_class"
                      value={formData.building_class}
                      onChange={handleChange}
                      className={getInputClasses(!!formErrors.building_class)}
                    >
                      <option value="" className="bg-slate-950 text-slate-400">
                        Select building class
                      </option>
                      {buildingClassOptions.map((buildingClass) => (
                        <option
                          key={buildingClass}
                          value={buildingClass}
                          className="bg-slate-950 text-white"
                        >
                          {buildingClass}
                        </option>
                      ))}
                    </select>
                    <FieldError message={formErrors.building_class} />
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
                      className={getInputClasses(!!formErrors.year_built)}
                    />
                    <FieldError message={formErrors.year_built} />
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
                      className={getInputClasses(!!formErrors.gross_sqft)}
                    />
                    <FieldError message={formErrors.gross_sqft} />
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
                      className={getInputClasses(!!formErrors.land_sqft)}
                    />
                    <FieldError message={formErrors.land_sqft} />
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
                      className={getInputClasses(!!formErrors.latitude)}
                    />
                    <FieldError message={formErrors.latitude} />
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
                      className={getInputClasses(!!formErrors.longitude)}
                    />
                    <FieldError message={formErrors.longitude} />
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
                      className={getInputClasses(!!formErrors.market_price)}
                    />
                    <FieldError message={formErrors.market_price} />
                  </div>
                </div>
              </div>

              <div className="flex justify-center">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isLoading ? 'Running Analysis...' : 'Run Analysis'}
                </button>
              </div>

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
                      {score}/100
                    </p>

                    {scoreCategory ? (
                      <div
                        className={`mt-4 inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${scoreCategory.classes}`}
                      >
                        {scoreCategory.label}
                      </div>
                    ) : null}

                    <p className="mt-4 text-sm text-slate-400">
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