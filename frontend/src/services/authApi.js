/**
 * Ensures the FastAPI `profiles` row exists for the current Supabase user.
 * The backend creates it on first GET /auth/me — call this after sign-in / session restore.
 */
import { supabase } from '../lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function ensureBackendProfile() {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  const token = session?.access_token
  if (!token) return

  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    // eslint-disable-next-line no-console
    console.warn('[PropIntel] GET /auth/me failed:', res.status, text)
  }
}
