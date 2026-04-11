import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchAdminOverview } from '../../services/adminApi'

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'admin-token' } },
      }),
    },
  },
}))

const BASE = 'http://localhost:8000'

describe('fetchAdminOverview()', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('sends GET /admin/overview with Bearer token', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total_users: 42, total_properties: 10 }),
    })

    const result = await fetchAdminOverview()

    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe(`${BASE}/admin/overview`)
    expect(options.headers['Authorization']).toBe('Bearer admin-token')
    expect(result.total_users).toBe(42)
  })

  it('throws with FORBIDDEN_ADMIN code on 403', async () => {
    fetch.mockResolvedValueOnce({ ok: false, status: 403 })

    await expect(fetchAdminOverview()).rejects.toMatchObject({ code: 'FORBIDDEN_ADMIN' })
  })

  it('throws with detail message on other non-ok response', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
    })

    await expect(fetchAdminOverview()).rejects.toThrow('Internal server error')
  })

  it('throws with fallback message when no detail field', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    })

    await expect(fetchAdminOverview()).rejects.toThrow('Request failed')
  })
})
