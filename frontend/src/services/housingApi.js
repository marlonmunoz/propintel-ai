import { apiFetch } from '../lib/apiClient'

/**
 * Find nearest property row from backend housing_data by coordinates.
 */
export async function lookupHousing({ lat, lng, borough }) {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
  })
  if (borough) params.set('borough', borough)

  return apiFetch(`/housing/lookup?${params.toString()}`, {
    method: 'GET',
    errorFallback: 'No nearby property found',
  })
}

