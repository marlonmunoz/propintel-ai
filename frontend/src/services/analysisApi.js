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

export async function analyzeProperty(payload) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_BASE_URL}/analyze-property-v2`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    let errorMessage = 'Failed to analyze property'
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // Keep fallback message
    }
    throw new Error(errorMessage)
  }

  return await response.json()
}
