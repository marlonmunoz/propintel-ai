import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchProfile, updateProfile } from '../../services/authApi'

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

describe('authApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  describe('fetchProfile()', () => {
    it('sends GET to /auth/me with Bearer token', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 'u1', display_name: 'Marlon' }),
      })

      const result = await fetchProfile()

      const [url, options] = fetch.mock.calls[0]
      expect(url).toBe(`${BASE}/auth/me`)
      expect(options.headers['Authorization']).toBe('Bearer test-token')
      expect(result.display_name).toBe('Marlon')
    })

    it('throws with status text on non-ok response', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => 'Unauthorized',
      })

      await expect(fetchProfile()).rejects.toThrow('Unauthorized')
    })
  })

  describe('updateProfile()', () => {
    it('sends PATCH to /auth/me with the payload', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ display_name: 'New Name' }),
      })

      const result = await updateProfile({ display_name: 'New Name' })

      const [url, options] = fetch.mock.calls[0]
      expect(url).toBe(`${BASE}/auth/me`)
      expect(options.method).toBe('PATCH')
      expect(JSON.parse(options.body)).toEqual({ display_name: 'New Name' })
      expect(result.display_name).toBe('New Name')
    })

    it('throws with error detail on failure', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Validation error' }),
      })

      await expect(updateProfile({})).rejects.toThrow('Validation error')
    })
  })
})
