import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

if (!API_BASE_URL) {
  console.error(
    '[propintel] VITE_API_BASE_URL is not set. ' +
    'Create frontend/.env with VITE_API_BASE_URL=http://127.0.0.1:8000 for local dev, ' +
    'or set it at build time for production.'
  )
}

// Module-level token cache — written by AuthContext via setSessionToken() on
// every auth state change so getAuthHeaders() never needs to await getSession().
let _cachedToken = null

/**
 * Called by AuthContext whenever the Supabase session changes.
 * Keeps the module-level cache in sync without any async work at call time.
 * @param {string | null} token
 */
export function setSessionToken(token) {
  _cachedToken = token ?? null
}

/**
 * Headers for FastAPI calls.
 * @param {Record<string, string>} [extra]
 * @param {{ allowApiKeyFallback?: boolean }} [opts] - If false, no X-API-Key when logged out (use for /auth/*).
 */
export async function getAuthHeaders(extra = {}, { allowApiKeyFallback = true } = {}) {
  // Read from cache first; fall back to a live getSession() only when the
  // cache is empty (e.g. very first call before AuthContext has mounted).
  let token = _cachedToken
  if (!token) {
    const { data: { session } } = await supabase.auth.getSession()
    token = session?.access_token ?? null
  }
  const base = {
    'Content-Type': 'application/json',
    ...extra,
  }
  if (token) {
    return { ...base, Authorization: `Bearer ${token}` }
  }
  if (allowApiKeyFallback && import.meta.env.DEV && import.meta.env.VITE_API_KEY) {
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

// Gateway-level errors worth retrying — the request never reached the app.
// 500 Internal Server Error is intentionally excluded: the server ran the
// handler and it crashed, so retrying a POST could cause duplicate side-effects.
const RETRYABLE_STATUS = new Set([502, 503, 504])
const MAX_RETRIES = 1
const RETRY_DELAY_MS = 800

/**
 * JSON fetch helper: attaches auth, throws Error with best-effort message on failure.
 *
 * - Pass `signal` (AbortSignal) to cancel in-flight requests on navigation /
 *   component unmount.  Wire it from a `useEffect` cleanup AbortController.
 * - Automatically retries once on transient 5xx errors (500/502/503/504)
 *   after a short delay.  Retry is skipped when the signal has been aborted.
 *
 * @param {string} path - e.g. `/analyze-property-v2` (no base URL)
 * @param {RequestInit & { json?: unknown, errorFallback?: string, authAllowApiKeyFallback?: boolean, signal?: AbortSignal }} options
 */
export async function apiFetch(path, options = {}) {
  const {
    json,
    headers: headerOverrides,
    errorFallback,
    authAllowApiKeyFallback = true,
    signal,
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

  const url = `${API_BASE_URL}${path}`
  const init = {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    signal,
  }

  let lastResponse
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    // Do not retry if the caller has already aborted the request.
    if (signal?.aborted) {
      throw new DOMException('Request was aborted', 'AbortError')
    }

    lastResponse = await fetch(url, init)

    // 204 No Content — treat as success immediately.
    if (lastResponse.status === 204) {
      return undefined
    }

    if (lastResponse.ok) {
      return lastResponse.json()
    }

    // Retry on transient server errors — but not if this was the last attempt
    // or if the status is not in our retryable set.
    if (attempt < MAX_RETRIES && RETRYABLE_STATUS.has(lastResponse.status)) {
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS))
      continue
    }

    break
  }

  const message = await parseApiErrorMessage(lastResponse, errorFallback ?? null)
  const err = new Error(message)
  err.status = lastResponse.status
  throw err
}
