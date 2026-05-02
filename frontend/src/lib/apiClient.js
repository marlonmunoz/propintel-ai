import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

if (!API_BASE_URL) {
  console.error(
    '[propintel] VITE_API_BASE_URL is not set. ' +
    'Create frontend/.env with VITE_API_BASE_URL=http://127.0.0.1:8000 for local dev, ' +
    'or set it at build time for production.'
  )
}

/**
 * Headers for FastAPI calls.
 * @param {Record<string, string>} [extra]
 * @param {{ allowApiKeyFallback?: boolean }} [opts] - If false, no X-API-Key when logged out (use for /auth/*).
 */
export async function getAuthHeaders(extra = {}, { allowApiKeyFallback = true } = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const token = session?.access_token
  const base = {
    'Content-Type': 'application/json',
    ...extra,
  }
  if (token) {
    return { ...base, Authorization: `Bearer ${token}` }
  }
  if (allowApiKeyFallback && import.meta.env.VITE_API_KEY) {
    return { ...base, 'X-API-Key': import.meta.env.VITE_API_KEY }
  }
  return base
}

/**
 * Parse FastAPI / Starlette error bodies (JSON detail or plain text).
 * @param {Response} response
 * @param {string | null} [fallbackMessage]
 */
export async function parseApiErrorMessage(response, fallbackMessage = null) {
  const code = typeof response.status === 'number' ? response.status : 'error'
  let raw = ''
  if (typeof response.text === 'function') {
    raw = await response.text().catch(() => '')
  } else if (typeof response.json === 'function') {
    try {
      raw = JSON.stringify(await response.json())
    } catch {
      raw = ''
    }
  }
  const trimmed = String(raw).trim()
  if (trimmed) {
    try {
      const data = JSON.parse(trimmed)
      const d = data.detail
      if (typeof d === 'string' && d.trim()) {
        return d.trim()
      }
      if (Array.isArray(d) && d.length) {
        return d.map((item) => item.msg ?? JSON.stringify(item)).join('; ')
      }
      if (data.message && String(data.message).trim()) {
        return String(data.message).trim()
      }
    } catch {
      return trimmed
    }
  }
  return fallbackMessage ?? `Request failed (${code})`
}

/**
 * JSON fetch helper: attaches auth, throws Error with best-effort message on failure.
 *
 * @param {string} path - e.g. `/analyze-property-v2` (no base URL)
 * @param {RequestInit & { json?: unknown, errorFallback?: string, authAllowApiKeyFallback?: boolean }} options
 */
export async function apiFetch(path, options = {}) {
  const {
    json,
    headers: headerOverrides,
    errorFallback,
    authAllowApiKeyFallback = true,
    ...rest
  } = options
  const headers = await getAuthHeaders(headerOverrides, {
    allowApiKeyFallback: authAllowApiKeyFallback,
  })

  if (!API_BASE_URL) {
    throw new Error(
      'API is not configured. Set VITE_API_BASE_URL in your frontend .env file.'
    )
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })

  // 204 No Content — treat as success before `ok` (some test mocks set ok inconsistently).
  if (response.status === 204) {
    return undefined
  }

  if (!response.ok) {
    const message = await parseApiErrorMessage(response, errorFallback ?? null)
    const err = new Error(message)
    err.status = response.status
    throw err
  }

  return response.json()
}
