import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { BookmarkPlus, CheckCircle2, MapPin, Sparkles } from 'lucide-react'
import { analyzeProperty } from '../services/analysisApi'
import { createProperty, getProperties } from '../services/propertiesApi'
import Navbar from '../components/Navbar'
import DealLabelBadge from '../components/DealLabelBadge'

const boroughOptions = [
  'Bronx',
  'Brooklyn',
  'Manhattan',
  'Queens',
  'Staten Island',
]

const buildingClassOptions = [
  { label: 'Single Family Home',          value: '01 ONE FAMILY DWELLINGS' },
  { label: 'Two Family Home',             value: '02 TWO FAMILY DWELLINGS' },
  { label: 'Three Family Home',           value: '03 THREE FAMILY DWELLINGS' },
  { label: 'Rental — Walkup',             value: '07 RENTALS - WALKUP APARTMENTS' },
  { label: 'Rental — Elevator Building',  value: '08 RENTALS - ELEVATOR APARTMENTS' },
  { label: 'Co-op — Walkup',              value: '09 COOPS - WALKUP APARTMENTS' },
  { label: 'Co-op — Elevator Building',   value: '10 COOPS - ELEVATOR APARTMENTS' },
  { label: 'Condo — Elevator Building',   value: '13 CONDOS - ELEVATOR APARTMENTS' },
  { label: 'Condo — Walkup',              value: '12 CONDOS - WALKUP APARTMENTS' },
]

const initialForm = {
  borough: '',
  neighborhood: '',
  building_class: '',
  year_built: '',
  gross_sqft: '',
  land_sqft: '',
  total_units: '',
  latitude: '',
  longitude: '',
  market_price: '',
}

const RENTAL_CLASSES = new Set([
  '07 RENTALS - WALKUP APARTMENTS',
  '08 RENTALS - ELEVATOR APARTMENTS',
])

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


// NYC bounding box — restricts Mapbox results to the 5 boroughs only.
// Format: [west, south, east, north]. Swap to lat/lng order when reading results.
// To expand to all of NYC + NJ someday, just widen this box.
const NYC_BBOX = '-74.259090,40.477399,-73.700009,40.917577'
// Bias autocomplete toward Manhattan / city core (lng,lat for Mapbox proximity).
const NYC_PROXIMITY = '-74.0060,40.7128'

// Mapbox returns NYC boroughs as "locality" context items.
// "The Bronx" is the official Mapbox label — we normalize it to match our dropdown.
function parseBoroughFromFeature(feature) {
  const context = feature.context || []
  const locality = context.find((c) => c.id?.startsWith('locality.'))
  if (!locality) return ''
  const name = locality.text
  if (name === 'The Bronx') return 'Bronx'
  const valid = ['Manhattan', 'Brooklyn', 'Queens', 'Staten Island', 'Bronx']
  return valid.includes(name) ? name : ''
}

// Mapbox returns neighborhood as a "neighborhood" context item.
// Falls back to "locality" (borough name) if no neighborhood is found —
// better than leaving the field empty.
function parseNeighborhoodFromFeature(feature) {
  const context = feature.context || []
  const nbhd = context.find((c) => c.id?.startsWith('neighborhood.'))
  return nbhd?.text || ''
}

// Mapbox includes NYC zip codes as "postcode" context items.
// Returns the 5-digit zip string, or empty string if not found.
function parseZipFromFeature(feature) {
  const context = feature.context || []
  const postcode = context.find((c) => c.id?.startsWith('postcode.'))
  return postcode?.text || ''
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

function getScoreCategory(score) {
  if (score >= 80) return { label: 'Strong', classes: 'border-lime-500/30 bg-lime-500/15 text-lime-700 dark:text-lime-300' }
  if (score >= 60) return { label: 'Moderate', classes: 'border-cyan-500/30 bg-cyan-500/15 text-cyan-700 dark:text-cyan-300' }
  if (score >= 40) return { label: 'Cautious', classes: 'border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-300' }
  return { label: 'Weak', classes: 'border-rose-500/30 bg-rose-500/15 text-rose-700 dark:text-rose-300' }
}

function StatCard({ label, value, tone = 'default' }) {
  const toneClasses =
    tone === 'positive'
      ? 'border-emerald-500/20 bg-emerald-500/10'
      : tone === 'negative'
        ? 'border-rose-500/20 bg-rose-500/10'
        : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950'

  return (
    <div className={`rounded-xl border p-4 ${toneClasses}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-xl font-bold text-slate-900 dark:text-white">{value}</p>
    </div>
  )
}

function FieldError({ message }) {
  if (!message) return null
  return <p className="mt-2 text-sm text-rose-500 dark:text-rose-300">{message}</p>
}

function getInputClasses(hasError) {
  return `w-full rounded-xl border bg-white px-4 py-3 text-slate-900 outline-none transition dark:bg-slate-950 dark:text-white ${
    hasError
      ? 'border-rose-400 focus:border-rose-400'
      : 'border-slate-300 focus:border-cyan-500 dark:border-slate-700 dark:focus:border-cyan-400'
  }`
}

function validateForm(formData) {
  const errors = {}

  if (!formData.borough.trim()) errors.borough = 'Borough is required.'
  if (!formData.neighborhood.trim()) errors.neighborhood = 'Neighborhood is required.'
  if (!formData.building_class.trim()) errors.building_class = 'Building class is required.'

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
  } else if (Number.isNaN(latitude) || latitude < 40.0 || latitude > 41.5) {
    errors.latitude = 'Latitude must be within NYC bounds (40.0 – 41.5).'
  }

  const longitude = Number(formData.longitude)
  if (!formData.longitude) {
    errors.longitude = 'Longitude is required.'
  } else if (Number.isNaN(longitude) || longitude < -75.0 || longitude > -73.0) {
    errors.longitude = 'Longitude must be within NYC bounds (−75.0 – −73.0).'
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
  const [isSaving, setIsSaving] = useState(false)
  const [savedToPortfolio, setSavedToPortfolio] = useState(false)
  const [saveError, setSaveError] = useState('')

  // Address search state
  // addressQuery: the full Mapbox place_name (e.g. "123 Main St, Brooklyn, NY 11201")
  // addressZip: 5-digit zip extracted from the selected Mapbox feature
  // suggestions: array of Mapbox feature results
  // isSearching: shows a subtle loading indicator while the API is in flight
  // showSuggestions: controls dropdown visibility
  const [addressQuery, setAddressQuery] = useState('')
  const [addressZip, setAddressZip] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)

  // true while the backend housing/lookup call is in flight after address selection.
  // Shown as a subtle banner so the user knows the form is being filled.
  const [isFetchingProperty, setIsFetchingProperty] = useState(false)

  // useRef stores the debounce timer ID across renders without triggering re-renders.
  // If we used useState for this, every keystroke would cause an extra render.
  const debounceRef = useRef(null)

  function handleChange(event) {
    const { name, value } = event.target
    setFormData((prev) => ({ ...prev, [name]: value }))
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
    setAddressQuery('')
    setAddressZip('')
    setSuggestions([])
  }

  // Called on every keystroke in the search box.
  // Clears the previous debounce timer and starts a new one — so the API
  // is only called 400ms after the user STOPS typing, not on every character.
  function handleAddressInputChange(e) {
    const query = e.target.value
    setAddressQuery(query)
    setShowSuggestions(true)

    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (!query || query.length < 3) {
      setSuggestions([])
      return
    }

    debounceRef.current = setTimeout(() => fetchSuggestions(query), 400)
  }

  // Calls the Mapbox Geocoding v5 REST API directly — no SDK needed.
  // bbox restricts results to NYC only. types=address means we only get
  // street addresses back, not parks, businesses, etc.
  async function fetchSuggestions(query) {
    const token = import.meta.env.VITE_MAPBOX_TOKEN
    if (!token) return
    setIsSearching(true)
    try {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
        query,
      )}.json?bbox=${NYC_BBOX}&country=US&types=address&limit=8&proximity=${NYC_PROXIMITY}&access_token=${token}`
      const res = await fetch(url)
      const data = await res.json()
      setSuggestions(data.features || [])
    } catch {
      setSuggestions([])
    } finally {
      setIsSearching(false)
    }
  }

  // Called when the user clicks a suggestion.
  // Step 1: fill location fields immediately from Mapbox (instant — no extra API call).
  // Step 2: call our backend housing/lookup to fill property details from PLUTO data.
  // Mapbox feature.center is [longitude, latitude] — note the order is lng first.
  function handleSelectSuggestion(feature) {
    const [lng, lat] = feature.center
    const borough = parseBoroughFromFeature(feature)
    const neighborhood = parseNeighborhoodFromFeature(feature)
    const zip = parseZipFromFeature(feature)

    setAddressQuery(feature.place_name)
    setAddressZip(zip)
    setSuggestions([])
    setShowSuggestions(false)

    setFormData((prev) => ({
      ...prev,
      latitude: String(lat.toFixed(6)),
      longitude: String(lng.toFixed(6)),
      ...(borough && { borough }),
      ...(neighborhood && { neighborhood }),
    }))

    setFormErrors((prev) => {
      const next = { ...prev }
      delete next.latitude
      delete next.longitude
      if (borough) delete next.borough
      if (neighborhood) delete next.neighborhood
      return next
    })

    // Call our backend with the lat/lng Mapbox just gave us.
    // Borough is passed as a filter so we only match properties in the same borough.
    fetchPropertyDetails(lat, lng, borough)
  }

  // Calls our own FastAPI backend to find the nearest property in housing_data
  // to the given coordinates. Uses our PLUTO-derived dataset — no third-party
  // API needed. Borough filter prevents cross-water false matches.
  // On success: fills year_built, gross_sqft, land_sqft, building_class, neighborhood.
  // On failure or no match: silently does nothing — fields stay blank for manual entry.
  async function fetchPropertyDetails(lat, lng, borough) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL
    const apiKey  = import.meta.env.VITE_API_KEY
    if (!baseUrl) return
    setIsFetchingProperty(true)
    try {
      const params = new URLSearchParams({ lat, lng })
      if (borough) params.set('borough', borough)
      const url = `${baseUrl}/housing/lookup?${params}`
      const res = await fetch(url, { headers: { 'X-API-Key': apiKey } })
      if (!res.ok) return
      const data = await res.json()

      setFormData((prev) => ({
        ...prev,
        ...(data.year_built                && { year_built:     String(data.year_built) }),
        ...(data.gross_sqft                && { gross_sqft:     String(Math.round(data.gross_sqft)) }),
        ...(data.land_sqft  !== undefined  && { land_sqft:      String(Math.round(data.land_sqft ?? 0)) }),
        ...(data.total_units               && { total_units:    String(Math.round(data.total_units)) }),
        ...(data.building_class            && { building_class: data.building_class }),
        ...(data.neighborhood              && { neighborhood:   data.neighborhood }),
      }))

      setFormErrors((prev) => {
        const next = { ...prev }
        if (data.year_built)                delete next.year_built
        if (data.gross_sqft)                delete next.gross_sqft
        if (data.land_sqft !== undefined)   delete next.land_sqft
        if (data.building_class)            delete next.building_class
        if (data.neighborhood)              delete next.neighborhood
        return next
      })
    } catch {
      // Silently fail — user fills manually
    } finally {
      setIsFetchingProperty(false)
    }
  }

  function buildPayload() {
    return {
      borough: formData.borough.trim(),
      neighborhood: formData.neighborhood.trim(),
      building_class: formData.building_class.trim(),
      year_built: Number(formData.year_built),
      gross_sqft: Number(formData.gross_sqft),
      land_sqft: Number(formData.land_sqft),
      // total_units is only sent when filled — used by rental models to compute
      // price_per_unit. Omit rather than send 0 so the backend can detect absence.
      ...(formData.total_units ? { total_units: Number(formData.total_units) } : {}),
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
    setSavedToPortfolio(false)
    setSaveError('')

    try {
      const payload = buildPayload()
      const result = await analyzeProperty(payload)
      setAnalysisResult(result)
    } catch (err) {
      setError(err.message || 'Something went wrong while analyzing.')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSaveToPortfolio() {
    if (!analysisResult) return
    setIsSaving(true)
    setSaveError('')

    // Use the full Mapbox place_name when the user selected from suggestions.
    // Fall back to "Neighborhood, Borough" only when fields were entered manually.
    const address = addressQuery.trim() || `${formData.neighborhood.trim()}, ${formData.borough.trim()}`
    const zipcode = addressZip || 'N/A'

    try {
      const existing = await getProperties({ limit: 50 })
      const isDuplicate = existing.some(
        (p) => p.address === address && p.listing_price === Number(formData.market_price)
      )
      if (isDuplicate) {
        setSavedToPortfolio(true)
        return
      }

      await createProperty({
        address,
        zipcode,
        bedrooms: 0,
        bathrooms: 0,
        sqft: Number(formData.gross_sqft) || 1,
        listing_price: Number(formData.market_price),
        analysis: analysisResult,
      })
      setSavedToPortfolio(true)
    } catch (err) {
      setSaveError(err.message || 'Failed to save. Please try again.')
    } finally {
      setIsSaving(false)
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
    <main className="min-h-screen bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />
      <section className="mx-auto max-w-7xl px-6 pb-12 pt-24">
        <div className="mb-10 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">
              PropIntel AI
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Property Analysis Workspace
            </h1>
            <p className="mt-3 max-w-2xl text-slate-500 dark:text-slate-300">
              Enter property details below to prepare an analysis request for the
              <span className="mx-1 font-semibold text-slate-900 dark:text-white">
                /analyze-property-v2
              </span>
              endpoint.
            </p>
          </div>

          <Link
            to="/"
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-white dark:hover:border-slate-500 dark:hover:bg-slate-900"
          >
            Back Home
          </Link>
        </div>

        <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          {/* Form panel */}
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
            <div>
              <h2 className="text-2xl font-semibold">Analysis Form</h2>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Fill in the property inputs required by the v2 analysis contract.
              </p>
              <br />
              <p className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                sample presets
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {Object.keys(samplePresets).map((presetName) => (
                  <button
                    key={presetName}
                    type="button"
                    onClick={() => handleUsePreset(presetName)}
                    className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-sm font-semibold text-cyan-700 transition hover:bg-cyan-500/20 dark:text-cyan-300"
                  >
                    {presetName}
                  </button>
                ))}

                <button
                  type="button"
                  onClick={handleResetForm}
                  className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 dark:border-slate-700 dark:text-white dark:hover:border-slate-500 dark:hover:bg-slate-900"
                >
                  Reset Form
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="mt-6 space-y-6" noValidate>

              {/* Address Search — auto-fills borough, neighborhood, lat, lng */}
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                  Find Property
                </h3>
                <p className="mt-1 mb-3 text-xs text-slate-500 dark:text-slate-400">
                  Type an NYC street address to auto-fill borough, neighborhood, coordinates, and — when
                  available — building attributes from our dataset.
                </p>
                {!import.meta.env.VITE_MAPBOX_TOKEN ? (
                  <div className="mb-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
                    Add <code className="rounded bg-amber-500/20 px-1">VITE_MAPBOX_TOKEN</code> to{' '}
                    <code className="rounded bg-amber-500/20 px-1">frontend/.env</code> to enable address
                    search (free tier at mapbox.com).
                  </div>
                ) : null}
                <div className="relative">
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={addressQuery}
                      onChange={handleAddressInputChange}
                      onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                      onBlur={() => setShowSuggestions(false)}
                      placeholder="123 Main St, Brooklyn…"
                      className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-9 pr-4 text-sm text-slate-900 outline-none transition focus:border-cyan-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:border-cyan-400"
                    />
                    {isSearching && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                        Searching…
                      </span>
                    )}
                  </div>

                  {/* Suggestions dropdown */}
                  {/* onMouseDown with e.preventDefault() is key here —
                      it prevents the input's onBlur from firing before the
                      click registers, which would close the dropdown too early */}
                  {showSuggestions && suggestions.length > 0 && (
                    <ul className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
                      {suggestions.map((feature, index) => (
                        <li key={`${feature.id}-${index}`}>
                          <button
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault()
                              handleSelectSuggestion(feature)
                            }}
                            className="flex w-full items-start gap-2 px-4 py-3 text-left text-sm text-slate-700 transition hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                          >
                            <MapPin className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-400" />
                            <span>{feature.place_name}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Loading banner — shown while backend housing/lookup is in flight.
                  Appears between the search box and the form fields so the user knows
                  the form is about to populate. Disappears once the call completes. */}
              {isFetchingProperty && (
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-700 dark:text-cyan-300">
                  Fetching property details…
                </div>
              )}

              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                  Property Basics
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="borough" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
                      Borough
                    </label>
                    <select
                      id="borough"
                      name="borough"
                      value={formData.borough}
                      onChange={handleChange}
                      className={getInputClasses(!!formErrors.borough)}
                    >
                      <option value="">Select borough</option>
                      {boroughOptions.map((borough) => (
                        <option key={borough} value={borough}>{borough}</option>
                      ))}
                    </select>
                    <FieldError message={formErrors.borough} />
                  </div>

                  <div>
                    <label htmlFor="neighborhood" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
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
                    <label htmlFor="building_class" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
                      Property Type
                    </label>
                    <select
                      id="building_class"
                      name="building_class"
                      value={formData.building_class}
                      onChange={handleChange}
                      className={getInputClasses(!!formErrors.building_class)}
                    >
                      <option value="">Select Property Type</option>
                      {buildingClassOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <FieldError message={formErrors.building_class} />
                  </div>

                  <div>
                    <label htmlFor="year_built" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
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
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                  Size &amp; Location
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="gross_sqft" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
                      Building Size (sq ft)
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
                    <label htmlFor="land_sqft" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
                      Lot Size (sq ft)
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

                  {/* Total units — shown for all building types but highlighted for
                      rental classes where it's used to reconstruct the full price */}
                  <div>
                    <label htmlFor="total_units" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
                      Total Units
                      {RENTAL_CLASSES.has(formData.building_class) && (
                        <span className="ml-2 text-xs font-normal text-cyan-600 dark:text-cyan-400">
                          required for rental valuation
                        </span>
                      )}
                    </label>
                    <input
                      id="total_units"
                      name="total_units"
                      type="number"
                      value={formData.total_units}
                      onChange={handleChange}
                      placeholder="e.g. 12"
                      className={getInputClasses(false)}
                    />
                  </div>

                  <div>
                    <label htmlFor="latitude" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
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
                    <label htmlFor="longitude" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
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
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                  Pricing
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="market_price" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">
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
                <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-200">
                  {error}
                </div>
              ) : null}
            </form>
          </div>

          {/* Results panel */}
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold">Analysis Results</h2>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                  Real backend results appear here after the analysis request completes.
                </p>
              </div>

              {hasV2Result ? (
                <div className="flex flex-wrap items-center gap-3">
                  <DealLabelBadge label={dealLabel} />
                  {score !== undefined && score !== null ? (
                    <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                      Investment score <span className="text-slate-900 dark:text-white">{score}</span>
                      /100
                    </span>
                  ) : null}
                </div>
              ) : null}
            </div>

            {!analysisResult && !isLoading ? (
              <div className="mt-6 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
                Submit the form to fetch valuation, investment score, drivers,
                and explanation from the v2 backend.
              </div>
            ) : null}

            {isLoading ? (
              <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                Loading analysis...
              </div>
            ) : null}

            {analysisResult && !hasV2Result && !isLoading ? (
              <div className="mt-6 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-200">
                The API returned a response, but it did not match the expected
                v2 grouped shape. Open the browser console and inspect
                <span className="mx-1 font-semibold text-slate-900 dark:text-white">
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
                    value={formatCurrency(analysisResult.valuation.predicted_price)}
                  />
                  <StatCard
                    label="Market Price"
                    value={formatCurrency(analysisResult.valuation.market_price)}
                  />
                  <StatCard
                    label="Price Difference"
                    value={formatCurrency(analysisResult.valuation.price_difference)}
                    tone={difference >= 0 ? 'positive' : 'negative'}
                  />
                  <StatCard
                    label="Difference %"
                    value={formatPercent(analysisResult.valuation.price_difference_pct)}
                    tone={analysisResult.valuation.price_difference_pct >= 0 ? 'positive' : 'negative'}
                  />
                </div>

                {analysisResult.valuation.price_low != null &&
                analysisResult.valuation.price_high != null ? (
                  <div className="rounded-2xl border border-cyan-500/25 bg-cyan-500/5 p-5 dark:border-cyan-500/30 dark:bg-cyan-950/30">
                    <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700 dark:text-cyan-400">
                      Estimated valuation range
                    </p>
                    <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                      {formatCurrency(analysisResult.valuation.price_low)}
                      <span className="mx-2 font-normal text-slate-400 dark:text-slate-500">–</span>
                      {formatCurrency(analysisResult.valuation.price_high)}
                    </p>
                    {analysisResult.valuation.valuation_interval_note ? (
                      <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                        {analysisResult.valuation.valuation_interval_note}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Investment Score
                    </p>
                    <p className="mt-4 text-5xl font-bold text-slate-900 dark:text-white">
                      {score}/100
                    </p>
                    {scoreCategory ? (
                      <div className={`mt-4 inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${scoreCategory.classes}`}>
                        {scoreCategory.label}
                      </div>
                    ) : null}
                    <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
                      Confidence:{' '}
                      <span className="font-semibold text-slate-900 dark:text-white">
                        {analysisResult.investment_analysis.confidence}
                      </span>
                    </p>
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                      Recommendation:{' '}
                      <span className="font-semibold text-slate-900 dark:text-white">
                        {analysisResult.investment_analysis.recommendation}
                      </span>
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
                    <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                      Investment Summary
                    </p>
                    <p className="mt-4 text-base leading-7 text-slate-700 dark:text-slate-200">
                      {analysisResult.investment_analysis.analysis_summary}
                    </p>
                    <div className="mt-5 grid gap-4 sm:grid-cols-2">
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          ROI Estimate
                        </p>
                        <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
                          {formatPercent(analysisResult.investment_analysis.roi_estimate)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Model Version
                        </p>
                        <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
                          {analysisResult.metadata.model_version}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                      Top Drivers
                    </h3>
                    <ul className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                      {analysisResult.drivers.top_drivers.map((driver) => (
                        <li
                          key={driver}
                          className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70"
                        >
                          {driver}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                      Model Context
                    </h3>
                    <ul className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                      {analysisResult.drivers.global_context.map((item) => (
                        <li
                          key={item}
                          className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70"
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 animate-pulse text-amber-400 drop-shadow-[0_0_10px_rgba(252,211,77,0.35)]" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                      AI Explanation
                    </h3>
                  </div>
                  <div className="mt-4 grid gap-4 xl:grid-cols-3">
                    {[
                      { label: 'Summary', text: analysisResult.explanation.summary },
                      { label: 'Opportunity', text: analysisResult.explanation.opportunity },
                      { label: 'Risks', text: analysisResult.explanation.risks },
                    ].map(({ label, text }) => (
                      <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          {label}
                        </p>
                        <p className="mt-3 text-sm leading-7 text-slate-600 dark:text-slate-300">
                          {text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 dark:border-slate-800 dark:bg-slate-950">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">Save to Portfolio</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Store this analysis so you can review it later without re-running the model.
                    </p>
                  </div>
                  {savedToPortfolio ? (
                    <div className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-4 w-4" />
                      Saved
                    </div>
                  ) : (
                    <button
                      onClick={handleSaveToPortfolio}
                      disabled={isSaving}
                      className="flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
                    >
                      <BookmarkPlus className="h-4 w-4" />
                      {isSaving ? 'Saving…' : 'Save'}
                    </button>
                  )}
                </div>
                {saveError ? (
                  <p className="text-sm text-rose-500 dark:text-rose-400">{saveError}</p>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  )
}
