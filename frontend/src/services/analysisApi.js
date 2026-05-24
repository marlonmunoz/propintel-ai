import { apiFetch } from '../lib/apiClient'

export async function analyzeProperty(payload) {
  return apiFetch('/analyze-property-v2', {
    method: 'POST',
    json: payload,
    errorFallback: 'Failed to analyze property',
  })
}

/**
 * Fetch the AI narrative explanation for an already-completed analysis.
 *
 * Pass the pre-computed values from the fast /analyze-property-v2 response so
 * the backend can call OpenAI without re-running the ML model.
 *
 * @param {{ predicted_price: number, market_price: number, roi_estimate: number, investment_score: number, top_drivers: string[] }} data
 */
export async function fetchExplanation(data) {
  return apiFetch('/analyze-property-v2/explanation', {
    method: 'POST',
    json: data,
    errorFallback: 'Failed to load AI explanation',
  })
}
