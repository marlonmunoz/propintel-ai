import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// ── Supabase mock ──────────────────────────────────────────────────────────
const mockGetSession = vi.hoisted(() => vi.fn())
const mockOnAuthStateChange = vi.hoisted(() =>
  vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } })
)
const mockSignOut = vi.hoisted(() => vi.fn().mockResolvedValue({}))

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signOut: mockSignOut,
    },
  },
}))

// ── authApi mock ────────────────────────────────────────────────────────────
const mockFetchProfile = vi.hoisted(() => vi.fn())
const mockFetchQuota = vi.hoisted(() => vi.fn())

vi.mock('../../services/authApi', () => ({
  fetchProfile: mockFetchProfile,
  fetchQuota: mockFetchQuota,
}))

import { AuthProvider, useAuth } from '../../context/AuthContext'

// Helper component that exposes context state via data-testid attributes
function Consumer() {
  const { user, profile, quota, loading } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user?.email ?? 'null'}</span>
      <span data-testid="profile-role">{profile?.role ?? 'null'}</span>
      <span data-testid="quota-remaining">{quota?.remaining ?? 'null'}</span>
    </div>
  )
}

function SignOutConsumer() {
  const { profile, quota, signOut } = useAuth()
  return (
    <div>
      <span data-testid="profile">{profile ? 'present' : 'null'}</span>
      <span data-testid="quota">{quota ? 'present' : 'null'}</span>
      <button onClick={signOut}>Sign out</button>
    </div>
  )
}

function renderProvider(children) {
  return render(
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  })
})

describe('AuthContext — loading state', () => {
  it('starts as loading=true then resolves to false', async () => {
    mockGetSession.mockResolvedValueOnce({ data: { session: null } })
    mockFetchProfile.mockResolvedValue(null)
    mockFetchQuota.mockResolvedValue(null)

    renderProvider(<Consumer />)
    expect(screen.getByTestId('loading').textContent).toBe('true')
    await waitFor(() =>
      expect(screen.getByTestId('loading').textContent).toBe('false')
    )
  })
})

describe('AuthContext — profile', () => {
  it('fetches profile when session exists', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: { access_token: 'tok', user: { email: 'a@b.com' } } },
    })
    mockFetchProfile.mockResolvedValue({ role: 'paid', display_name: 'Alice' })
    mockFetchQuota.mockResolvedValue(null)

    renderProvider(<Consumer />)
    await waitFor(() =>
      expect(screen.getByTestId('profile-role').textContent).toBe('paid')
    )
  })

  it('sets profile to null when fetchProfile throws', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: { access_token: 'tok', user: { email: 'a@b.com' } } },
    })
    mockFetchProfile.mockRejectedValue(new Error('network error'))
    mockFetchQuota.mockResolvedValue(null)

    renderProvider(<Consumer />)
    await waitFor(() =>
      expect(screen.getByTestId('profile-role').textContent).toBe('null')
    )
  })

  it('does not fetch profile when no session', async () => {
    mockGetSession.mockResolvedValueOnce({ data: { session: null } })
    mockFetchProfile.mockResolvedValue({ role: 'user' })
    mockFetchQuota.mockResolvedValue(null)

    renderProvider(<Consumer />)
    await waitFor(() =>
      expect(screen.getByTestId('loading').textContent).toBe('false')
    )
    expect(mockFetchProfile).not.toHaveBeenCalled()
  })
})

describe('AuthContext — quota', () => {
  it('fetches quota when session exists', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: { access_token: 'tok', user: { email: 'a@b.com' } } },
    })
    mockFetchProfile.mockResolvedValue({ role: 'user' })
    mockFetchQuota.mockResolvedValue({
      role: 'user',
      daily_limit: 10,
      used_today: 4,
      remaining: 6,
      resets_at: '2026-04-12',
    })

    renderProvider(<Consumer />)
    await waitFor(() =>
      expect(screen.getByTestId('quota-remaining').textContent).toBe('6')
    )
  })

  it('sets quota to null when fetchQuota returns null', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: { access_token: 'tok', user: { email: 'a@b.com' } } },
    })
    mockFetchProfile.mockResolvedValue({ role: 'user' })
    mockFetchQuota.mockResolvedValue(null)

    renderProvider(<Consumer />)
    await waitFor(() =>
      expect(screen.getByTestId('loading').textContent).toBe('false')
    )
    expect(screen.getByTestId('quota-remaining').textContent).toBe('null')
  })

  it('does not fetch quota when no session', async () => {
    mockGetSession.mockResolvedValueOnce({ data: { session: null } })
    mockFetchProfile.mockResolvedValue(null)
    mockFetchQuota.mockResolvedValue({ remaining: 5 })

    renderProvider(<Consumer />)
    await waitFor(() =>
      expect(screen.getByTestId('loading').textContent).toBe('false')
    )
    expect(mockFetchQuota).not.toHaveBeenCalled()
  })
})

describe('AuthContext — signOut', () => {
  it('clears profile and quota on sign-out', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: { access_token: 'tok', user: { email: 'a@b.com' } } },
    })
    mockFetchProfile.mockResolvedValue({ role: 'user' })
    mockFetchQuota.mockResolvedValue({ remaining: 5 })

    const { getByRole } = renderProvider(<SignOutConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('profile').textContent).toBe('present')
    })

    await act(async () => {
      getByRole('button', { name: /sign out/i }).click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('profile').textContent).toBe('null')
      expect(screen.getByTestId('quota').textContent).toBe('null')
    })
  })
})
