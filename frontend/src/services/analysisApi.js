const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
const API_KEY = import.meta.env.VITE_API_KEY

export async function analyzeProperty(payload) {
  const response = await fetch(`${API_BASE_URL}/analyze-property-v2`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    let errorMessage = 'Failed to analyze property'

    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorMessage
    } catch {
      // Keep fallback message if response is not valid JSON
    }

    throw new Error(errorMessage)
  }

  const data = await response.json()
  return data
}