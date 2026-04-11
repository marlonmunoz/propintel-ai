import { describe, it, expect, vi, beforeEach } from 'vitest'
import { recordMapboxGeocodeUsage } from '../../services/geocodeUsageApi'

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'user-token' } },
      }),
    },
  },
}))

const BASE = 'http://localhost:8000'

describe('recordMapboxGeocodeUsage()', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('sends POST /geocode/usage with Bearer token', async () => {
    fetch.mockResolvedValueOnce({ ok: true, status: 204 })

    await recordMapboxGeocodeUsage()

    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe(`${BASE}/geocode/usage`)
    expect(options.method).toBe('POST')
    expect(options.headers['Authorization']).toBe('Bearer user-token')
  })

  it('resolves without throwing on 204', async () => {
    fetch.mockResolvedValueOnce({ ok: false, status: 204 })
    await expect(recordMapboxGeocodeUsage()).resolves.toBeUndefined()
  })

  it('throws on non-ok, non-204 response (e.g. 429 cap exceeded)', async () => {
    fetch.mockResolvedValueOnce({ ok: false, status: 429 })
    await expect(recordMapboxGeocodeUsage()).rejects.toThrow('Geocode usage recording failed')
  })

  it('sends request body as empty JSON object', async () => {
    fetch.mockResolvedValueOnce({ ok: true, status: 204 })
    await recordMapboxGeocodeUsage()
    const [, options] = fetch.mock.calls[0]
    expect(options.body).toBe('{}')
  })
})
