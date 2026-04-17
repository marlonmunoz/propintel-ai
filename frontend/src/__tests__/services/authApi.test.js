import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockUpdateUser = vi.hoisted(() => vi.fn())
const mockReauthenticate = vi.hoisted(() => vi.fn())

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
      updateUser: (...args) => mockUpdateUser(...args),
      reauthenticate: (...args) => mockReauthenticate(...args),
    },
  },
}))

import {
  fetchProfile,
  updateProfile,
  changePassword,
  requestPasswordReauthNonce,
  isPasswordChangeReauthRequired,
} from '../../services/authApi'

const BASE = 'http://localhost:8000'

describe('authApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    mockUpdateUser.mockReset()
    mockReauthenticate.mockReset()
    mockUpdateUser.mockResolvedValue({ data: { user: {} }, error: null })
    mockReauthenticate.mockResolvedValue({ error: null })
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

  describe('changePassword()', () => {
    it('calls updateUser with password and current_password', async () => {
      await changePassword({ currentPassword: 'old', newPassword: 'newnewnew' })
      expect(mockUpdateUser).toHaveBeenCalledWith({
        password: 'newnewnew',
        current_password: 'old',
      })
    })

    it('includes nonce when provided', async () => {
      await changePassword({
        currentPassword: 'old',
        newPassword: 'newnewnew',
        nonce: '123456',
      })
      expect(mockUpdateUser).toHaveBeenCalledWith({
        password: 'newnewnew',
        current_password: 'old',
        nonce: '123456',
      })
    })

    it('throws when updateUser returns error', async () => {
      mockUpdateUser.mockResolvedValueOnce({
        data: { user: null },
        error: { message: 'Invalid password', status: 400 },
      })
      await expect(
        changePassword({ currentPassword: 'wrong', newPassword: 'newnewnew' })
      ).rejects.toMatchObject({ message: 'Invalid password' })
    })
  })

  describe('requestPasswordReauthNonce()', () => {
    it('calls reauthenticate', async () => {
      await requestPasswordReauthNonce()
      expect(mockReauthenticate).toHaveBeenCalled()
    })

    it('throws on error', async () => {
      mockReauthenticate.mockResolvedValueOnce({ error: { message: 'Rate limited' } })
      await expect(requestPasswordReauthNonce()).rejects.toThrow('Rate limited')
    })
  })

  describe('isPasswordChangeReauthRequired()', () => {
    it('returns true for 401 with reauthentication message', () => {
      expect(
        isPasswordChangeReauthRequired({
          status: 401,
          message: 'Password update requires reauthentication',
        })
      ).toBe(true)
    })

    it('returns false for wrong password style errors', () => {
      expect(
        isPasswordChangeReauthRequired({
          status: 400,
          message: 'Invalid credentials',
        })
      ).toBe(false)
    })
  })
})
