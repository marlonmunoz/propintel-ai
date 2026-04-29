import { apiFetch } from '../lib/apiClient'

export async function analyzeProperty(payload) {
  return apiFetch('/analyze-property-v2', {
    method: 'POST',
    json: payload,
    errorFallback: 'Failed to analyze property',
  })
}
