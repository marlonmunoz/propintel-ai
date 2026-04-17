import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}))

vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockResolvedValue({}),
  fetchQuota: vi.fn().mockResolvedValue(null),
  updateProfile: vi.fn().mockResolvedValue({}),
  changePassword: vi.fn().mockResolvedValue(undefined),
  requestPasswordReauthNonce: vi.fn().mockResolvedValue(undefined),
  isPasswordChangeReauthRequired: vi.fn(() => false),
}))

const mockUseAuth = vi.hoisted(() => vi.fn())

vi.mock('../../context/AuthContext', () => ({
  useAuth: mockUseAuth,
}))

import Profile from '../../pages/Profile'

function renderProfile(profileOverrides = {}, quotaOverrides = null) {
  mockUseAuth.mockReturnValue({
    user: { email: 'test@example.com' },
    profile: { role: 'user', display_name: '', marketing_opt_in: false, ...profileOverrides },
    quota: quotaOverrides,
    refreshProfile: vi.fn(),
  })
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Profile />
      </ThemeProvider>
    </MemoryRouter>
  )
}

describe('Profile page — tier badge', () => {
  it('shows Free plan for role=user', () => {
    renderProfile({ role: 'user' })
    expect(screen.getByText('Free')).toBeTruthy()
    expect(screen.getByText(/Up to 10 AI/)).toBeTruthy()
  })

  it('shows Paid plan for role=paid', () => {
    renderProfile({ role: 'paid' })
    // "Paid" appears in both the Navbar badge and the tier pill — both are correct
    expect(screen.getAllByText('Paid').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Up to 200 AI/)).toBeTruthy()
  })

  it('shows Admin plan for role=admin', () => {
    renderProfile({ role: 'admin' })
    // "Admin" appears in both the Navbar badge and the tier pill — both are correct
    expect(screen.getAllByText('Admin').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/unlimited AI analyses/i)).toBeTruthy()
  })
})

describe('Profile page — quota bar', () => {
  it('shows used / limit when quota is present', () => {
    renderProfile(
      { role: 'user' },
      { daily_limit: 10, used_today: 3, remaining: 7, resets_at: '2026-04-12' }
    )
    expect(screen.getByText(/3/)).toBeTruthy()
    expect(screen.getByText(/7 remaining today/)).toBeTruthy()
  })

  it('shows Unlimited for null daily_limit', () => {
    renderProfile(
      { role: 'admin' },
      { daily_limit: null, used_today: 0, remaining: null, resets_at: '2026-04-12' }
    )
    expect(screen.getByText('Unlimited')).toBeTruthy()
  })

  it('shows quota reached message when remaining is 0', () => {
    renderProfile(
      { role: 'user' },
      { daily_limit: 10, used_today: 10, remaining: 0, resets_at: '2026-04-12' }
    )
    expect(screen.getByText(/Quota reached for today/)).toBeTruthy()
  })

  it('renders nothing quota-related when quota is null', () => {
    renderProfile({ role: 'user' }, null)
    expect(screen.queryByText(/remaining today/)).toBeNull()
    expect(screen.queryByText('Unlimited')).toBeNull()
  })
})

describe('Profile page — change password', () => {
  it('renders the Change password section', () => {
    renderProfile({ role: 'user' })
    expect(screen.getByRole('heading', { name: /Change password/i })).toBeTruthy()
    expect(screen.getByLabelText(/Current password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^New password$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Update password/i })).toBeInTheDocument()
  })
})

describe('Profile page — upgrade CTA', () => {
  it('shows upgrade CTA for free users', () => {
    renderProfile({ role: 'user' })
    expect(screen.getByText(/Upgrade to Paid/)).toBeTruthy()
    expect(screen.getByText(/Stripe payment integration/)).toBeTruthy()
  })

  it('hides upgrade CTA for paid users', () => {
    renderProfile({ role: 'paid' })
    expect(screen.queryByText(/Stripe payment integration/)).toBeNull()
  })

  it('hides upgrade CTA for admin users', () => {
    renderProfile({ role: 'admin' })
    expect(screen.queryByText(/Stripe payment integration/)).toBeNull()
  })
})
