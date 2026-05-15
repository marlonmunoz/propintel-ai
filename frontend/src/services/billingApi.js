/**
 * Stripe billing — hosted Checkout & Customer Portal (URLs from backend).
 */
import { apiFetch } from '../lib/apiClient'

const BILLING_OPTS = { authAllowApiKeyFallback: false }

/** @returns {Promise<{ url: string }>} */
export async function createCheckoutSession() {
  return apiFetch('/billing/checkout', {
    method: 'POST',
    ...BILLING_OPTS,
    errorFallback: 'Could not start checkout',
  })
}

/** @returns {Promise<{ url: string }>} */
export async function createPortalSession() {
  return apiFetch('/billing/portal', {
    method: 'POST',
    ...BILLING_OPTS,
    errorFallback: 'Could not open billing portal',
  })
}
