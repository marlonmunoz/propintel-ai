import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Headers for authenticated FastAPI calls: Bearer from Supabase session, else X-API-Key.
 */
export async function getAuthHeaders(extra = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const token = session?.access_token
  return {
    'Content-Type': 'application/json',
    ...(token
      ? { Authorization: `Bearer ${token}` }
      : { 'X-API-Key': import.meta.env.VITE_API_KEY }),
    ...extra,
  }
}

/**
 * Parse FastAPI / Starlette error JSON into a single message string.
 * @param {Response} response
 * @param {string | null} [fallbackMessage] - Used when body has no usable detail (e.g. per-endpoint UX copy).
 */
export async function parseApiErrorMessage(response, fallbackMessage = null) {
  try {
    const data = await response.json()
    const d = data.detail
    if (typeof d === 'string' && d.trim()) {
      return d
    }
    if (Array.isArray(d) && d.length) {
      return d.map((item) => item.msg ?? JSON.stringify(item)).join('; ')
    }
    if (data.message && String(data.message).trim()) {
      return String(data.message)
    }
  } catch {
    // use fallback below
  }
  const code = typeof response.status === 'number' ? response.status : 'error'
  return fallbackMessage ?? `Request failed (${code})`
}

/**
 * JSON fetch helper: attaches auth, throws Error with best-effort message on failure.
 *
 * @param {string} path - e.g. `/analyze-property-v2` (no base URL)
 * @param {RequestInit & { json?: unknown }} options
 */
export async function apiFetch(path, options = {}) {
  const { json, headers: headerOverrides, errorFallback, ...rest } = options
  const headers = await getAuthHeaders(headerOverrides)

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })

  if (!response.ok) {
    const message = await parseApiErrorMessage(response, errorFallback ?? null)
    const err = new Error(message)
    err.status = response.status
    throw err
  }

  if (response.status === 204) {
    return undefined
  }

  return response.json()
}
