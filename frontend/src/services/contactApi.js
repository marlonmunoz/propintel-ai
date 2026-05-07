/**
 * Contact-form API service.
 *
 * The /contact endpoint is fully public (no auth required), so this module
 * uses plain fetch rather than the authenticated apiFetch helper.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Send a contact-form message to the backend.
 *
 * @param {{ name: string, email: string, topic: 'support'|'partnerships', message: string }} payload
 * @returns {Promise<{ ok: boolean, message: string }>}
 * @throws {Error} with a human-readable message on failure
 */
export async function sendContactMessage({ name, email, topic, message }) {
  if (!API_BASE_URL) {
    throw new Error('API is not configured — please contact us by email directly.')
  }

  const response = await fetch(`${API_BASE_URL}/contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, topic, message }),
  })

  if (!response.ok) {
    let msg = 'Failed to send message. Please try again or email us directly.'
    try {
      const data = await response.json()
      if (typeof data.detail === 'string' && data.detail.trim()) {
        msg = data.detail.trim()
      } else if (typeof data.message === 'string' && data.message.trim()) {
        msg = data.message.trim()
      }
    } catch {
      // ignore JSON parse error — keep the generic message above
    }
    throw new Error(msg)
  }

  return response.json()
}
