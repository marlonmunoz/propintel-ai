import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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
}))

const mockFetchAdminOverview = vi.hoisted(() => vi.fn())
vi.mock('../../services/adminApi', () => ({
  fetchAdminOverview: mockFetchAdminOverview,
}))

const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('../../context/AuthContext', () => ({
  useAuth: mockUseAuth,
}))

import AdminDashboard from '../../pages/AdminDashboard'

const OVERVIEW_FIXTURE = {
  as_of: '2026-04-11T12:00:00Z',
  profiles_count: 12,
  properties_count: 34,
  llm: {
    today_total_calls: 5,
    today_users_with_calls: 3,
    quota_free_per_day: 10,
    quota_paid_per_day: 200,
  },
  mapbox: {
    today_total_requests: 8,
    today_users_with_requests: 2,
    requests_last_7_days_total: 55,
    requests_month_to_date_utc: 200,
    monthly_free_requests_cap: 100000,
    month_utc_label: 'Apr 2026',
  },
}

function renderDashboard(profileRole = 'admin') {
  mockUseAuth.mockReturnValue({
    user: { email: 'admin@test.com' },
    profile: { role: profileRole, display_name: 'Admin' },
    quota: null,
    signOut: vi.fn(),
  })

  return render(
    <MemoryRouter>
      <ThemeProvider>
        <AdminDashboard />
      </ThemeProvider>
    </MemoryRouter>
  )
}

describe('AdminDashboard page', () => {
  it('renders Admin Overview heading', async () => {
    mockFetchAdminOverview.mockResolvedValueOnce(OVERVIEW_FIXTURE)
    renderDashboard()
    await waitFor(() =>
      expect(screen.getByText(/Admin Overview/i)).toBeInTheDocument()
    )
  })

  it('displays Profiles stat label after data loads', async () => {
    mockFetchAdminOverview.mockResolvedValueOnce(OVERVIEW_FIXTURE)
    renderDashboard()
    await waitFor(() =>
      expect(screen.getByText('Profiles')).toBeInTheDocument()
    )
  })

  it('displays Saved properties stat label after data loads', async () => {
    mockFetchAdminOverview.mockResolvedValueOnce(OVERVIEW_FIXTURE)
    renderDashboard()
    await waitFor(() =>
      expect(screen.getByText('Saved properties')).toBeInTheDocument()
    )
  })

  it('shows error message when API call fails', async () => {
    mockFetchAdminOverview.mockRejectedValueOnce(new Error('Server error'))
    renderDashboard()
    await waitFor(() =>
      expect(screen.getByText(/Server error/i)).toBeInTheDocument()
    )
  })

  it('renders Refresh button', async () => {
    mockFetchAdminOverview.mockResolvedValueOnce(OVERVIEW_FIXTURE)
    renderDashboard()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument()
    )
  })
})
