import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getProperties,
  createProperty,
  updateProperty,
  deleteProperty,
} from '../../services/propertiesApi'

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

describe('propertiesApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  describe('getProperties()', () => {
    it('sends GET to /properties/', async () => {
      fetch.mockResolvedValueOnce({ ok: true, json: async () => [] })

      await getProperties()

      const [url, options] = fetch.mock.calls[0]
      expect(url).toBe(`${BASE}/properties/`)
      expect(options.headers['Authorization']).toBe('Bearer test-token')
    })

    it('appends query string params', async () => {
      fetch.mockResolvedValueOnce({ ok: true, json: async () => [] })

      await getProperties({ page: 2, limit: 10 })

      const [url] = fetch.mock.calls[0]
      expect(url).toContain('page=2')
      expect(url).toContain('limit=10')
    })

    it('throws on error response', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Unauthorized' }),
      })

      await expect(getProperties()).rejects.toThrow('Unauthorized')
    })
  })

  describe('createProperty()', () => {
    it('sends POST to /properties/ with JSON body', async () => {
      const prop = { address: '1 Test St', borough: 'Brooklyn' }
      fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ id: 1, ...prop }) })

      await createProperty(prop)

      const [url, options] = fetch.mock.calls[0]
      expect(url).toBe(`${BASE}/properties/`)
      expect(options.method).toBe('POST')
      expect(JSON.parse(options.body)).toEqual(prop)
    })
  })

  describe('updateProperty()', () => {
    it('sends PATCH to /properties/:id', async () => {
      fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ id: 5 }) })

      await updateProperty(5, { address: 'Updated' })

      const [url, options] = fetch.mock.calls[0]
      expect(url).toBe(`${BASE}/properties/5`)
      expect(options.method).toBe('PATCH')
    })
  })

  describe('deleteProperty()', () => {
    it('sends DELETE to /properties/:id', async () => {
      fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) })

      await deleteProperty(7)

      const [url, options] = fetch.mock.calls[0]
      expect(url).toBe(`${BASE}/properties/7`)
      expect(options.method).toBe('DELETE')
    })
  })
})
