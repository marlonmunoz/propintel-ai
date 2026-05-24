import { Link } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import PropertyLocationMap from './PropertyLocationMap'
import {
  boroughOptions,
  buildingClassOptions,
  samplePresets,
  RENTAL_CLASSES,
} from '../pages/analyzeConstants'

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

/**
 * Left panel of the Analyze page — the property input form.
 *
 * All state lives in the parent (Analyze.jsx).  This component is purely
 * presentational: it fires callbacks and renders whatever props it receives.
 */
export default function AnalyzeForm({
  // form state
  formData,
  formErrors,
  onFieldChange,
  onSubmit,
  isLoading,
  error,
  quota,
  // presets + reset
  onUsePreset,
  onReset,
  // address geocoder (from useAddressGeocoder hook)
  addressQuery,
  suggestions,
  isSearching,
  showSuggestions,
  onAddressInputChange,
  onAddressInputFocus,
  onAddressInputBlur,
  onSelectSuggestion,
  // map
  onMapPinDragEnd,
  isFetchingProperty,
}) {
  return (
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
              onClick={() => onUsePreset(presetName)}
              className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-sm font-semibold text-cyan-700 transition hover:bg-cyan-500/20 dark:text-cyan-300"
            >
              {presetName}
            </button>
          ))}

          <button
            type="button"
            onClick={onReset}
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 dark:border-slate-700 dark:text-white dark:hover:border-slate-500 dark:hover:bg-slate-900"
          >
            Reset Form
          </button>
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-6 space-y-6" noValidate>

        {/* Address Search */}
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
                onChange={onAddressInputChange}
                onFocus={onAddressInputFocus}
                onBlur={onAddressInputBlur}
                placeholder="123 Main St, Brooklyn…"
                className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-9 pr-4 text-sm text-slate-900 outline-none transition focus:border-cyan-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:border-cyan-400"
              />
              {isSearching && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                  Searching…
                </span>
              )}
            </div>

            {/* Suggestions dropdown.
                onMouseDown with e.preventDefault() prevents the input's onBlur from
                firing before the click registers, which would close the dropdown early. */}
            {showSuggestions && suggestions.length > 0 && (
              <ul className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
                {suggestions.map((feature, index) => (
                  <li key={`${feature.id}-${index}`}>
                    <button
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault()
                        onSelectSuggestion(feature)
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

        {/* Location preview map */}
        <PropertyLocationMap
          lat={Number(formData.latitude) || null}
          lng={Number(formData.longitude) || null}
          onCoordinatesChange={onMapPinDragEnd}
        />

        {/* Property-details fetch banner */}
        {isFetchingProperty && (
          <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-700 dark:text-cyan-300">
            Fetching property details…
          </div>
        )}

        {/* Property Basics */}
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
                onChange={onFieldChange}
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
                onChange={onFieldChange}
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
                onChange={onFieldChange}
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
                onChange={onFieldChange}
                placeholder="1925"
                className={getInputClasses(!!formErrors.year_built)}
              />
              <FieldError message={formErrors.year_built} />
            </div>
          </div>
        </div>

        {/* Size & Location */}
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
                onChange={onFieldChange}
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
                onChange={onFieldChange}
                placeholder="2000"
                className={getInputClasses(!!formErrors.land_sqft)}
              />
              <FieldError message={formErrors.land_sqft} />
            </div>

            {/* Total units — optional for all types; required for rental
                classes where the dedicated rental model uses it */}
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
                onChange={onFieldChange}
                placeholder="e.g. 12"
                className={getInputClasses(!!formErrors.total_units)}
              />
              <FieldError message={formErrors.total_units} />
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
                onChange={onFieldChange}
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
                onChange={onFieldChange}
                placeholder="-73.9778"
                className={getInputClasses(!!formErrors.longitude)}
              />
              <FieldError message={formErrors.longitude} />
            </div>
          </div>
        </div>

        {/* Pricing */}
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
                onChange={onFieldChange}
                placeholder="1250000"
                className={getInputClasses(!!formErrors.market_price)}
              />
              <FieldError message={formErrors.market_price} />
            </div>
          </div>
          <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            Valuations and AI text are informational only — not an appraisal or professional advice.{' '}
            <Link to="/disclaimer" className="font-medium text-cyan-600 hover:underline dark:text-cyan-400">
              Read the full disclaimer
            </Link>
            .
          </p>
        </div>

        {/* Submit + quota pill */}
        <div className="flex flex-col items-center gap-3">
          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isLoading ? 'Running Analysis...' : 'Run Analysis'}
          </button>
          {quota && quota.daily_limit !== null && (
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${
              quota.remaining === 0
                ? 'border-rose-300 bg-rose-50 text-rose-600 dark:border-rose-700 dark:bg-rose-950/40 dark:text-rose-400'
                : quota.remaining <= 3
                  ? 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-400'
                  : 'border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400'
            }`}>
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                quota.remaining === 0
                  ? 'bg-rose-500'
                  : quota.remaining <= 3
                    ? 'bg-amber-500'
                    : 'bg-cyan-500'
              }`} />
              {quota.remaining === 0
                ? 'Daily AI quota reached — upgrade for more'
                : `${quota.remaining} of ${quota.daily_limit} AI analyses left today`}
            </span>
          )}
        </div>

        {error ? (
          <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-200">
            {error}
          </div>
        ) : null}
      </form>
    </div>
  )
}
