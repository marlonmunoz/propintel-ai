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
    console.warn('[PropIntel] ensureBackendProfile:', e)
  }
}

/** Fetches the current user's daily LLM quota status from GET /auth/quota. */
export async function fetchQuota() {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE_URL}/auth/quota`, { headers })
  if (!res.ok) return null
  return await res.json()
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

/**
 * True when GoTrue rejected a password update because a fresh session or OTP
 * nonce is required (Secure password change in Supabase Email settings).
 */
export function isPasswordChangeReauthRequired(error) {
  if (!error || typeof error !== 'object') return false
  const msg = String(error.message ?? '').toLowerCase()
  const code = String(error.code ?? '')
  const status = error.status ?? error.statusCode
  if (code === 'session_not_recent') return true
  if (status === 401 && msg.includes('reauthentication')) return true
  if (msg.includes('password update requires reauthentication')) return true
  return false
}

/** Sends a one-time code to the user's email for step 2 of password change. */
export async function requestPasswordReauthNonce() {
  const { error } = await supabase.auth.reauthenticate()
  if (error) throw new Error(error.message || 'Could not send verification code.')
}

/**
 * Updates the signed-in user's password via Supabase Auth.
 * Requires "Require current password" in dashboard: pass currentPassword.
 * If the server asks for reauthentication, call requestPasswordReauthNonce(), then
 * call again with the same passwords and nonce set to the email OTP.
 */
export async function changePassword({ currentPassword, newPassword, nonce }) {
  const attrs = {
    password: newPassword,
    current_password: currentPassword,
  }
  if (nonce) attrs.nonce = nonce
  const { error } = await supabase.auth.updateUser(attrs)
  if (error) throw error
}
