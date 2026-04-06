/**
 * Shared Supabase mock factory.
 * Import and call makeSbMock() inside vi.mock() factory functions.
 *
 * Usage in a test file:
 *   vi.mock('../../lib/supabase', () => ({ supabase: makeSbMock() }))
 */
import { vi } from 'vitest'

export function makeSbMock({ session = null } = {}) {
  const onAuthStateChangeSub = { unsubscribe: vi.fn() }

  return {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session } }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: onAuthStateChangeSub } }),
      signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
      signOut: vi.fn().mockResolvedValue({}),
    },
  }
}
