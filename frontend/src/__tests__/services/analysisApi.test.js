import { describe, it, expect, vi, beforeEach } from 'vitest'
import { analyzeProperty } from '../../services/analysisApi'

// Mock the Supabase client so getSession doesn't hit the network.
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

describe('analyzeProperty()', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('sends POST to /analyze-property-v2 with Authorization header', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ valuation: { estimated_value: 500000 } }),
    })

    const payload = { address: '123 Main St', borough: 'Manhattan' }
    await analyzeProperty(payload)

    expect(fetch).toHaveBeenCalledOnce()
    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe(`${BASE}/analyze-property-v2`)
    expect(options.method).toBe('POST')
    expect(options.headers['Authorization']).toBe('Bearer test-token')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(options.body)).toEqual(payload)
  })

  it('returns parsed JSON on success', async () => {
    const mockResponse = { valuation: { estimated_value: 750000 } }
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await analyzeProperty({ address: '456 Park Ave' })
    expect(result).toEqual(mockResponse)
  })

  it('throws an error with the API message on non-ok response', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Property not found' }),
    })

    await expect(analyzeProperty({ address: 'bad' })).rejects.toThrow('Property not found')
  })

  it('throws a fallback error when no detail field is present', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({}),
    })

    await expect(analyzeProperty({ address: 'bad' })).rejects.toThrow(
      'Failed to analyze property'
    )
  })

  it('uses X-API-Key header when there is no session', async () => {
    const { supabase } = await import('../../lib/supabase')
    supabase.auth.getSession.mockResolvedValueOnce({ data: { session: null } })

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    })

    await analyzeProperty({})
    const [, options] = fetch.mock.calls[0]
    expect(options.headers['X-API-Key']).toBe('test-api-key')
    expect(options.headers['Authorization']).toBeUndefined()
  })
})
