import { apiFetch } from '../lib/apiClient'

/**
 * Operational aggregates for the admin dashboard (GET /admin/overview).
 */
export async function fetchAdminOverview() {
  try {
    return await apiFetch('/admin/overview', {
      method: 'GET',
      errorFallback: 'Request failed',
    })
  } catch (e) {
    if (e.status === 403) {
      const err = new Error('Admin access required.')
      err.code = 'FORBIDDEN_ADMIN'
      throw err
    }
    throw e
  }
}
