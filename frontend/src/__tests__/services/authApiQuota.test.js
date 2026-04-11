import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchQuota } from '../../services/authApi'

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}))

const BASE = 'http://localhost:8000'

describe('fetchQuota()', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('sends GET to /auth/quota with Bearer token', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        role: 'user',
        daily_limit: 10,
        used_today: 3,
        remaining: 7,
        resets_at: '2026-04-12',
      }),
    })

    const result = await fetchQuota()

    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe(`${BASE}/auth/quota`)
    expect(options.headers['Authorization']).toBe('Bearer test-token')
    expect(result.role).toBe('user')
    expect(result.remaining).toBe(7)
  })

  it('returns null on non-ok response without throwing', async () => {
    fetch.mockResolvedValueOnce({ ok: false, status: 401 })
    const result = await fetchQuota()
    expect(result).toBeNull()
  })

  it('returns null on network error without throwing', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'))
    const result = await fetchQuota().catch(() => null)
    expect(result).toBeNull()
  })

  it('correctly maps admin unlimited response', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        role: 'admin',
        daily_limit: null,
        used_today: 0,
        remaining: null,
        resets_at: '2026-04-12',
      }),
    })

    const result = await fetchQuota()
    expect(result.daily_limit).toBeNull()
    expect(result.remaining).toBeNull()
  })
})
