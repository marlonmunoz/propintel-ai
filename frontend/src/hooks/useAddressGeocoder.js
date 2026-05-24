import { useState, useRef } from 'react'
import { recordMapboxGeocodeUsage } from '../services/geocodeUsageApi'

// NYC bounding box — restricts Mapbox results to the 5 boroughs only.
// Format: [west, south, east, north].
const NYC_BBOX = '-74.259090,40.477399,-73.700009,40.917577'
// Bias autocomplete toward Manhattan / city core (lng,lat for Mapbox proximity).
const NYC_PROXIMITY = '-74.0060,40.7128'

// Mapbox returns NYC boroughs as "locality" context items.
// "The Bronx" is the official Mapbox label — normalize it to match our dropdown.
function parseBoroughFromFeature(feature) {
  const context = feature.context || []
  const locality = context.find((c) => c.id?.startsWith('locality.'))
  if (!locality) return ''
  const name = locality.text
  if (name === 'The Bronx') return 'Bronx'
  const valid = ['Manhattan', 'Brooklyn', 'Queens', 'Staten Island', 'Bronx']
  return valid.includes(name) ? name : ''
}

function parseNeighborhoodFromFeature(feature) {
  const context = feature.context || []
  const nbhd = context.find((c) => c.id?.startsWith('neighborhood.'))
  return nbhd?.text || ''
}

function parseZipFromFeature(feature) {
  const context = feature.context || []
  const postcode = context.find((c) => c.id?.startsWith('postcode.'))
  return postcode?.text || ''
}

/**
 * Manages Mapbox address autocomplete state and API calls.
 *
 * @param {{ onSuggestionSelected: (params: { lat: number, lng: number, borough: string, neighborhood: string, zip: string }) => void }} options
 *   Callback fired when the user selects a suggestion.  The parent uses it to
 *   update form fields and trigger the housing/lookup backend call.
 */
export function useAddressGeocoder({ onSuggestionSelected }) {
  const [addressQuery, setAddressQuery] = useState('')
  const [addressZip, setAddressZip] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const debounceRef = useRef(null)

  function reset() {
    setAddressQuery('')
    setAddressZip('')
    setSuggestions([])
    setShowSuggestions(false)
  }

  // Called on every keystroke — debounces the API call by 400 ms so we only
  // hit Mapbox after the user stops typing, not on every character.
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
  // bbox restricts results to NYC; types=address means street addresses only.
  async function fetchSuggestions(query) {
    const token = import.meta.env.VITE_MAPBOX_TOKEN
    if (!token) return
    setIsSearching(true)
    try {
      const url =
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}` +
        `.json?bbox=${NYC_BBOX}&country=US&types=address&limit=8&proximity=${NYC_PROXIMITY}` +
        `&access_token=${token}`
      const res = await fetch(url)
      const data = await res.json()
      setSuggestions(data.features || [])
      if (res.ok) {
        void recordMapboxGeocodeUsage().catch((err) => {
          if (import.meta.env.DEV) {
            console.warn('[PropIntel] Geocode usage not recorded:', err?.message ?? err)
          }
        })
      }
    } catch {
      setSuggestions([])
    } finally {
      setIsSearching(false)
    }
  }

  // Called when the user clicks a suggestion.
  // Updates geocoder state, then calls onSuggestionSelected so the parent can
  // update the form fields and trigger the housing/lookup backend call.
  function handleSelectSuggestion(feature) {
    const [lng, lat] = feature.center
    const borough = parseBoroughFromFeature(feature)
    const neighborhood = parseNeighborhoodFromFeature(feature)
    const zip = parseZipFromFeature(feature)

    setAddressQuery(feature.place_name)
    setAddressZip(zip)
    setSuggestions([])
    setShowSuggestions(false)

    onSuggestionSelected({ lat, lng, borough, neighborhood, zip })
  }

  function handleInputFocus() {
    if (suggestions.length > 0) setShowSuggestions(true)
  }

  function handleInputBlur() {
    setShowSuggestions(false)
  }

  return {
    addressQuery,
    addressZip,
    suggestions,
    isSearching,
    showSuggestions,
    handleAddressInputChange,
    handleSelectSuggestion,
    handleInputFocus,
    handleInputBlur,
    reset,
  }
}
