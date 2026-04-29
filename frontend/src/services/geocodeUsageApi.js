import { apiFetch } from '../lib/apiClient'

/**
 * Record one Mapbox Geocoding forward-search request after a successful client call.
 * Fire-and-forget from the Analyze page; failures are ignored.
 */
export async function recordMapboxGeocodeUsage() {
  if (!import.meta.env.VITE_API_BASE_URL) return
  await apiFetch('/geocode/usage', {
    method: 'POST',
    json: {},
    errorFallback: 'Geocode usage recording failed',
  })
}
