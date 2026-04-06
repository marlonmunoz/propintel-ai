import { supabase } from '../lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Returns the correct auth headers for every API call.
 * - JWT users (logged in via Supabase):  Authorization: Bearer <access_token>
 * - Fallback (no session):               X-API-Key (dev / Postman use only)
 */
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

async function handleResponse(response) {
  if (!response.ok) {
    let message = 'Request failed'
    try {
      const data = await response.json()
      message = data.detail || data.message || message
    } catch {
      // Keep fallback
    }
    throw new Error(message)
  }
  return await response.json()
}

export async function getProperties(params = {}) {
  const headers = await getAuthHeaders()
  const query = new URLSearchParams(params).toString()
  const url = `${API_BASE_URL}/properties/${query ? '?' + query : ''}`
  const response = await fetch(url, { headers })
  return handleResponse(response)
}

export async function createProperty(payload) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}/properties/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}

export async function updateProperty(id, payload) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}/properties/${id}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}

export async function deleteProperty(id) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}/properties/${id}`, {
    method: 'DELETE',
    headers,
  })
  return handleResponse(response)
}
