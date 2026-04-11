import { supabase } from '../lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function getAuthHeaders() {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const token = session?.access_token
  return {
    ...(token
      ? { Authorization: `Bearer ${token}` }
      : { 'X-API-Key': import.meta.env.VITE_API_KEY }),
  }
}

/**
 * Record one Mapbox Geocoding forward-search request after a successful client call.
 * Fire-and-forget from the Analyze page; failures are ignored.
 */
export async function recordMapboxGeocodeUsage() {
  if (!API_BASE_URL) return
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE_URL}/geocode/usage`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: '{}',
  })
  if (!res.ok && res.status !== 204) {
    throw new Error('Geocode usage recording failed')
  }
}
