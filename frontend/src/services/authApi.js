/**
 * Backend profile (FastAPI `profiles` table) — GET/PATCH /auth/me.
 */
import { supabase } from '../lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function getAuthHeaders() {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  const token = session?.access_token
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/** Ensures a `profiles` row exists and returns the profile JSON. */
export async function fetchProfile() {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE_URL}/auth/me`, { headers })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `GET /auth/me failed (${res.status})`)
  }
  return await res.json()
}

/** @deprecated use fetchProfile — kept for call sites that only care about side effect */
export async function ensureBackendProfile() {
  try {
    await fetchProfile()
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[PropIntel] ensureBackendProfile:', e)
  }
}

export async function updateProfile(payload) {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let msg = 'Update failed'
    try {
      const data = await res.json()
      msg = data.detail || data.message || msg
    } catch {
      // ignore
    }
    throw new Error(msg)
  }
  return await res.json()
}
