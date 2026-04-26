import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  fetchProfile: vi.fn().mockResolvedValue({ role: 'user', display_name: null }),
  fetchQuota: vi.fn().mockResolvedValue(null),
}))

const mockGetProperties = vi.hoisted(() => vi.fn())
const mockDeleteProperty = vi.hoisted(() => vi.fn())

vi.mock('../../services/propertiesApi', () => ({
  getProperties: mockGetProperties,
  deleteProperty: mockDeleteProperty,
}))

vi.mock('../../utils/portfolioReportExport', () => ({
  downloadPropertyCsv: vi.fn(),
  downloadPropertyPdf: vi.fn(),
}))

vi.mock('../../utils/portfolioReportPrint', () => ({
  printPortfolioReport: vi.fn(),
}))

const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('../../context/AuthContext', () => ({
  useAuth: mockUseAuth,
}))

import Portfolio from '../../pages/Portfolio'

function renderPortfolio(properties = []) {
  mockUseAuth.mockReturnValue({
    user: { email: 'test@test.com' },
    profile: { role: 'user', display_name: null },
    quota: null,
    refreshProfile: vi.fn(),
    refreshQuota: vi.fn(),
    signOut: vi.fn(),
  })
  mockGetProperties.mockResolvedValue(properties)

  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Portfolio />
      </ThemeProvider>
    </MemoryRouter>
  )
}

describe('Portfolio page', () => {
  it('renders the Saved Analyses heading', async () => {
    renderPortfolio()
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /Saved Analyses/i })).toBeInTheDocument()
    )
  })

  it('shows empty state when no properties returned', async () => {
    renderPortfolio([])
    await waitFor(() =>
      expect(screen.getByText(/No saved analyses yet/i)).toBeInTheDocument()
    )
  })

  it('renders property cards when properties exist', async () => {
    const props = [
      {
        id: '1',
        address: '123 Main St',
        borough: 'Brooklyn',
        created_at: new Date().toISOString(),
        analysis: {
          investment_analysis: { deal_label: 'Buy', investment_score: 75 },
          valuation: { predicted_price: 1200000 },
        },
      },
    ]
    renderPortfolio(props)
    await waitFor(() =>
      expect(screen.getByText('123 Main St')).toBeInTheDocument()
    )
  })

  it('enables selection and opens compare panel (free tier limit=2)', async () => {
    const user = userEvent.setup()
    const props = [
      {
        id: '1',
        address: '41-17 Denman St',
        borough: 'Queens',
        created_at: new Date('2026-04-11T10:00:00Z').toISOString(),
        analysis: {
          investment_analysis: { deal_label: 'Avoid', investment_score: 0, roi_estimate: -25.0 },
          valuation: { predicted_price: 937774, market_price: 1250000, price_difference: -312226 },
        },
      },
      {
        id: '2',
        address: '123 Main St',
        borough: 'Brooklyn',
        created_at: new Date('2026-04-14T10:00:00Z').toISOString(),
        analysis: {
          investment_analysis: { deal_label: 'Buy', investment_score: 82, roi_estimate: 9.1 },
          valuation: { predicted_price: 1200000, market_price: 1100000, price_difference: 100000 },
        },
      },
      {
        id: '3',
        address: '55 Park Ave',
        borough: 'Manhattan',
        created_at: new Date('2026-04-20T10:00:00Z').toISOString(),
        analysis: {
          investment_analysis: { deal_label: 'Hold', investment_score: 51, roi_estimate: 1.7 },
          valuation: { predicted_price: 890000, market_price: 875000, price_difference: 15000 },
        },
      },
    ]
    renderPortfolio(props)

    await waitFor(() => expect(screen.getByText('41-17 Denman St')).toBeInTheDocument())

    const cb1 = screen.getByLabelText(/Select 41-17 Denman St for comparison/i)
    const cb2 = screen.getByLabelText(/Select 123 Main St for comparison/i)
    const cb3 = screen.getByLabelText(/Select 55 Park Ave for comparison/i)

    await user.click(cb1)
    await user.click(cb2)

    // Sticky bar should appear and allow compare.
    const compareBtn = screen.getByRole('button', { name: /Compare 2 properties/i })
    expect(compareBtn).toBeEnabled()

    // Free tier should block selecting a third.
    expect(cb3).toBeDisabled()

    await user.click(compareBtn)
    expect(screen.getByRole('dialog', { name: /Compare properties/i })).toBeInTheDocument()
    expect(screen.getByText(/Compare saved analyses — no quota used/i)).toBeInTheDocument()
  })

  it('shows sort dropdown when properties exist', async () => {
    const props = [
      {
        id: '2',
        address: '456 Park Ave',
        borough: 'Manhattan',
        created_at: new Date().toISOString(),
        analysis: { investment_analysis: { deal_label: 'Hold', investment_score: 55 }, valuation: { predicted_price: 900000 } },
      },
    ]
    renderPortfolio(props)
    await waitFor(() => {
      const select = document.querySelector('select')
      expect(select).not.toBeNull()
    })
  })
})
