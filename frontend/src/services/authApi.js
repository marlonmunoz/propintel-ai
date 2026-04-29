/**
 * Backend profile (FastAPI `profiles` table) — GET/PATCH /auth/me.
 */
import { supabase } from '../lib/supabase'
import { apiFetch } from '../lib/apiClient'

const AUTH_OPTS = { authAllowApiKeyFallback: false }

/** Ensures a `profiles` row exists and returns the profile JSON. */
export async function fetchProfile() {
  return apiFetch('/auth/me', {
    method: 'GET',
    ...AUTH_OPTS,
    errorFallback: 'Failed to load profile',
  })
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
  try {
    return await apiFetch('/auth/quota', {
      method: 'GET',
      ...AUTH_OPTS,
    })
  } catch {
    return null
  }
}

export async function updateProfile(payload) {
  return apiFetch('/auth/me', {
    method: 'PATCH',
    json: payload,
    ...AUTH_OPTS,
    errorFallback: 'Update failed',
  })
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
