import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { analyzeProperty, fetchExplanation } from '../services/analysisApi'
import { lookupHousing } from '../services/housingApi'
import { createProperty, getProperties } from '../services/propertiesApi'
import { useAuth } from '../context/AuthContext'
import { useAddressGeocoder } from '../hooks/useAddressGeocoder'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import AnalyzeForm from '../components/AnalyzeForm'
import AnalyzeResults from '../components/AnalyzeResults'
import { initialForm, samplePresets, getScoreCategory, validateForm } from './analyzeConstants'

export default function Analyze() {
  const { quota, refreshQuota } = useAuth()

  // ── Form state ──────────────────────────────────────────────────────────────
  const [formData, setFormData] = useState(initialForm)
  const [formErrors, setFormErrors] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // ── Results state ───────────────────────────────────────────────────────────
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isExplanationLoading, setIsExplanationLoading] = useState(false)
  const [explanationError, setExplanationError] = useState('')

  // ── Portfolio save state ────────────────────────────────────────────────────
  const [isSaving, setIsSaving] = useState(false)
  const [savedToPortfolio, setSavedToPortfolio] = useState(false)
  const [saveError, setSaveError] = useState('')

  // ── Property-details fetch banner ───────────────────────────────────────────
  const [isFetchingProperty, setIsFetchingProperty] = useState(false)

  // ── Address geocoder hook ───────────────────────────────────────────────────
  // The hook handles Mapbox API state.  When a suggestion is selected, we
  // update the form fields here and fire the housing/lookup backend call.
  const geocoder = useAddressGeocoder({
    onSuggestionSelected: ({ lat, lng, borough, neighborhood }) => {
      setFormData((prev) => ({
        ...prev,
        latitude:  String(lat.toFixed(6)),
        longitude: String(lng.toFixed(6)),
        ...(borough      && { borough }),
        ...(neighborhood && { neighborhood }),
      }))
      setFormErrors((prev) => {
        const next = { ...prev }
        delete next.latitude
        delete next.longitude
        if (borough)      delete next.borough
        if (neighborhood) delete next.neighborhood
        return next
      })
      fetchPropertyDetails(lat, lng, borough)
    },
  })

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleMapPinDragEnd = useCallback((nextLat, nextLng) => {
    setFormData((prev) => ({
      ...prev,
      latitude:  nextLat.toFixed(6),
      longitude: nextLng.toFixed(6),
    }))
    // The previously geocoded address no longer matches these coordinates —
    // clear it so buildPayload() doesn't send a stale address for the pin's
    // new location. geocoder.reset() only touches its own state setters,
    // which are stable across renders, so this is safe outside the deps array.
    geocoder.reset()
  }, [])

  function handleFieldChange(event) {
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
    // Merge into initialForm so every key stays defined — presets omit
    // total_units; replacing the whole object would make controlled inputs
    // switch from defined → undefined and trigger React warnings.
    const preset = samplePresets[presetName]
    if (!preset) return
    setFormData({ ...initialForm, ...preset })
    setFormErrors({})
    setError('')
    setAnalysisResult(null)
    // Presets set their own lat/lon directly — an address left over from an
    // earlier manual search would no longer match this property.
    geocoder.reset()
  }

  function handleResetForm() {
    setFormData(initialForm)
    setFormErrors({})
    setAnalysisResult(null)
    setError('')
    geocoder.reset()
  }

  // Calls our backend to find the nearest property in housing_data.
  // On success: fills year_built, gross_sqft, land_sqft, building_class,
  // neighborhood and the two unit counts.
  // On failure or no match: silently does nothing — fields stay blank for manual entry.
  async function fetchPropertyDetails(lat, lng, borough) {
    setIsFetchingProperty(true)
    try {
      const data = await lookupHousing({ lat, lng, borough })
      setFormData((prev) => ({
        ...prev,
        ...(data.year_built               && { year_built:     String(data.year_built) }),
        ...(data.gross_sqft               && { gross_sqft:     String(Math.round(data.gross_sqft)) }),
        ...(data.land_sqft !== undefined  && { land_sqft:      String(Math.round(data.land_sqft ?? 0)) }),
        ...(data.total_units              && { total_units:    String(Math.round(data.total_units)) }),
        ...(data.residential_units        && { residential_units: String(Math.round(data.residential_units)) }),
        ...(data.building_class           && { building_class: data.building_class }),
        ...(data.neighborhood             && { neighborhood:   data.neighborhood }),
      }))
      setFormErrors((prev) => {
        const next = { ...prev }
        if (data.year_built)               delete next.year_built
        if (data.gross_sqft)               delete next.gross_sqft
        if (data.land_sqft !== undefined)  delete next.land_sqft
        if (data.building_class)           delete next.building_class
        if (data.neighborhood)             delete next.neighborhood
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
      borough:       formData.borough.trim(),
      neighborhood:  formData.neighborhood.trim(),
      building_class: formData.building_class.trim(),
      year_built:    Number(formData.year_built),
      gross_sqft:    Number(formData.gross_sqft),
      land_sqft:     Number(formData.land_sqft),
      // total_units only sent when filled — rental models use it to compute
      // price_per_unit; omit rather than send 0 so the backend can detect absence.
      ...(formData.total_units ? { total_units: Number(formData.total_units) } : {}),
      // residential_units likewise omitted when blank so the model imputes it
      // instead of treating an empty field as a genuine zero-unit building.
      ...(formData.residential_units
        ? { residential_units: Number(formData.residential_units) }
        : {}),
      latitude:      Number(formData.latitude),
      longitude:     Number(formData.longitude),
      market_price:  Number(formData.market_price),
      // Sent so the backend can resolve a BBL server-side and unlock the
      // full Gold feature set (DOF/ACRIS/PLUTO) without any new form field.
      // addressQuery is cleared on preset selection and pin drag (see
      // handleUsePreset / handleMapPinDragEnd) so it can't outlive the
      // lat/lon it was originally geocoded for; the backend's resolver also
      // independently sanity-checks the resolved lot's coordinates against
      // latitude/longitude before trusting a match.
      ...(geocoder.addressQuery.trim() ? { address: geocoder.addressQuery.trim() } : {}),
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setExplanationError('')
    setAnalysisResult(null)
    setIsExplanationLoading(false)

    const validationErrors = validateForm(formData)
    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors)
      return
    }

    setFormErrors({})
    setIsLoading(true)
    setSavedToPortfolio(false)
    setSaveError('')

    // ── Phase 1: fast ML valuation (no LLM) ────────────────────────────────
    let fastResult = null
    try {
      const payload = buildPayload()
      fastResult = await analyzeProperty(payload)
      setAnalysisResult(fastResult)
      void refreshQuota()
    } catch (err) {
      setError(err.message || 'Something went wrong while analyzing.')
      setIsLoading(false)
      return
    }
    setIsLoading(false)

    // ── Phase 2: AI explanation (async, valuation already visible) ──────────
    setIsExplanationLoading(true)
    try {
      const explResult = await fetchExplanation({
        predicted_price:  fastResult.valuation.predicted_price,
        market_price:     fastResult.valuation.market_price,
        roi_estimate:     fastResult.investment_analysis.roi_estimate,
        investment_score: fastResult.investment_analysis.investment_score,
        top_drivers:      fastResult.drivers.top_drivers,
      })
      setAnalysisResult((prev) => ({
        ...prev,
        explanation:        explResult.explanation,
        explanation_status: explResult.explanation_status,
      }))
      void refreshQuota()
    } catch {
      setExplanationError('AI explanation could not be loaded. Please try again.')
    } finally {
      setIsExplanationLoading(false)
    }
  }

  async function handleSaveToPortfolio() {
    if (!analysisResult) return
    setIsSaving(true)
    setSaveError('')

    // Use the full Mapbox place_name when the user selected from suggestions.
    // Fall back to "Neighborhood, Borough" only for manual entry.
    const address =
      geocoder.addressQuery.trim() ||
      `${formData.neighborhood.trim()}, ${formData.borough.trim()}`
    const zipcode = geocoder.addressZip || 'N/A'

    try {
      const existing = await getProperties({ limit: 50 })
      const isDuplicate = existing.some(
        (p) => p.address === address && p.listing_price === Number(formData.market_price),
      )
      if (isDuplicate) {
        setSavedToPortfolio(true)
        return
      }

      await createProperty({
        address,
        zipcode,
        bedrooms:      0,
        bathrooms:     0,
        sqft:          Number(formData.gross_sqft) || 1,
        listing_price: Number(formData.market_price),
        analysis:      analysisResult,
      })
      setSavedToPortfolio(true)
    } catch (err) {
      setSaveError(err.message || 'Failed to save. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  // ── Derived display values ──────────────────────────────────────────────────
  const hasV2Result =
    Boolean(analysisResult?.valuation) &&
    Boolean(analysisResult?.investment_analysis) &&
    Boolean(analysisResult?.drivers) &&
    Boolean(analysisResult?.explanation)

  const dealLabel    = analysisResult?.investment_analysis?.deal_label
  const score        = analysisResult?.investment_analysis?.investment_score
  const scoreCategory = score !== undefined ? getScoreCategory(score) : null
  const difference   = analysisResult?.valuation?.price_difference ?? 0

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />
      <main className="flex-1">
        <section className="mx-auto max-w-7xl px-4 pb-12 pt-24 sm:px-6">
          <div className="mb-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
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
              className="shrink-0 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-white dark:hover:border-slate-500 dark:hover:bg-slate-900"
            >
              Back Home
            </Link>
          </div>

          {/*
            2-column split starts at lg (1024px) with a narrower sidebar so
            tablet-landscape/small-laptop widths aren't stuck with a single,
            very tall column; xl widens the sidebar back to its original size.
          */}
          <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)] xl:grid-cols-[420px_minmax(0,1fr)]">
            <AnalyzeForm
              formData={formData}
              formErrors={formErrors}
              onFieldChange={handleFieldChange}
              onSubmit={handleSubmit}
              isLoading={isLoading}
              error={error}
              quota={quota}
              onUsePreset={handleUsePreset}
              onReset={handleResetForm}
              addressQuery={geocoder.addressQuery}
              suggestions={geocoder.suggestions}
              isSearching={geocoder.isSearching}
              showSuggestions={geocoder.showSuggestions}
              onAddressInputChange={geocoder.handleAddressInputChange}
              onAddressInputFocus={geocoder.handleInputFocus}
              onAddressInputBlur={geocoder.handleInputBlur}
              onSelectSuggestion={geocoder.handleSelectSuggestion}
              onMapPinDragEnd={handleMapPinDragEnd}
              isFetchingProperty={isFetchingProperty}
            />

            <AnalyzeResults
              analysisResult={analysisResult}
              hasV2Result={hasV2Result}
              isLoading={isLoading}
              isExplanationLoading={isExplanationLoading}
              explanationError={explanationError}
              score={score}
              scoreCategory={scoreCategory}
              dealLabel={dealLabel}
              difference={difference}
              isSaving={isSaving}
              savedToPortfolio={savedToPortfolio}
              saveError={saveError}
              onSaveToPortfolio={handleSaveToPortfolio}
            />
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
