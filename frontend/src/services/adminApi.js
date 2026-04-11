import { supabase } from '../lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function getAuthHeaders() {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const token = session?.access_token
  return {
    'Content-Type': 'application/json',
    ...(token
      ? { Authorization: `Bearer ${token}` }
      : { 'X-API-Key': import.meta.env.VITE_API_KEY }),
  }
}

/**
 * Operational aggregates for the admin dashboard (GET /admin/overview).
 */
export async function fetchAdminOverview() {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE_URL}/admin/overview`, { headers })
  if (res.status === 403) {
    const err = new Error('Admin access required.')
    err.code = 'FORBIDDEN_ADMIN'
    throw err
  }
  if (!res.ok) {
    let message = 'Request failed'
    try {
      const data = await res.json()
      message = data.detail || data.message || message
    } catch {
      // keep fallback
    }
    throw new Error(message)
  }
  return res.json()
}
