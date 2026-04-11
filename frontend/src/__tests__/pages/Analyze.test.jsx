import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

// ── Supabase ────────────────────────────────────────────────────────────────
vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'tok', user: { email: 'u@test.com' } } },
      }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}))

// ── authApi ──────────────────────────────────────────────────────────────────
vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockResolvedValue({ role: 'user' }),
  fetchQuota: vi.fn().mockResolvedValue(null),
}))

// ── analysisApi ──────────────────────────────────────────────────────────────
const mockAnalyzeProperty = vi.hoisted(() => vi.fn())
vi.mock('../../services/analysisApi', () => ({
  analyzeProperty: mockAnalyzeProperty,
}))

// ── propertiesApi ────────────────────────────────────────────────────────────
vi.mock('../../services/propertiesApi', () => ({
  createProperty: vi.fn().mockResolvedValue({ id: 'p1' }),
  getProperties: vi.fn().mockResolvedValue([]),
}))

// ── geocodeUsageApi ──────────────────────────────────────────────────────────
vi.mock('../../services/geocodeUsageApi', () => ({
  recordMapboxGeocodeUsage: vi.fn().mockResolvedValue(undefined),
}))

// ── Mapbox (PropertyLocationMap uses WebGL which is not available in jsdom) ──
vi.mock('../../components/PropertyLocationMap', () => ({
  default: () => null,
}))

// ── AuthContext ──────────────────────────────────────────────────────────────
const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('../../context/AuthContext', () => ({
  useAuth: mockUseAuth,
}))

import Analyze from '../../pages/Analyze'

function renderAnalyze(quotaOverride = null) {
  mockUseAuth.mockReturnValue({
    user: { email: 'u@test.com' },
    profile: { role: 'user' },
    quota: quotaOverride,
    refreshQuota: vi.fn(),
    signOut: vi.fn(),
  })

  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Analyze />
      </ThemeProvider>
    </MemoryRouter>
  )
}

// ── Basic render ─────────────────────────────────────────────────────────────

describe('Analyze page — basic render', () => {
  it('renders the Run Analysis button', () => {
    renderAnalyze()
    expect(screen.getByRole('button', { name: /Run Analysis/i })).toBeInTheDocument()
  })

  it('renders the borough dropdown', () => {
    renderAnalyze()
    expect(screen.getByRole('combobox', { name: /borough/i })).toBeInTheDocument()
  })

  it('renders the empty results placeholder text', () => {
    renderAnalyze()
    expect(screen.getByText(/Submit the form to fetch/i)).toBeInTheDocument()
  })
})

// ── Quota pill ───────────────────────────────────────────────────────────────

describe('Analyze page — quota pill', () => {
  it('shows nothing when quota is null', () => {
    renderAnalyze(null)
    expect(screen.queryByText(/AI analyses left today/i)).toBeNull()
  })

  it('shows nothing when daily_limit is null (unlimited)', () => {
    renderAnalyze({ daily_limit: null, used_today: 0, remaining: null })
    expect(screen.queryByText(/AI analyses left today/i)).toBeNull()
  })

  it('shows remaining count pill for a free user with quota remaining', () => {
    renderAnalyze({ daily_limit: 10, used_today: 3, remaining: 7 })
    expect(screen.getByText(/7 of 10 AI analyses left today/i)).toBeInTheDocument()
  })

  it('shows exhausted message when remaining is 0', () => {
    renderAnalyze({ daily_limit: 10, used_today: 10, remaining: 0 })
    expect(screen.getByText(/Daily AI quota reached/i)).toBeInTheDocument()
  })

  it('pill is present as a span element (not a plain paragraph)', () => {
    renderAnalyze({ daily_limit: 10, used_today: 2, remaining: 8 })
    const pill = screen.getByText(/8 of 10 AI analyses left today/i)
    expect(pill.tagName.toLowerCase()).toBe('span')
  })
})

// ── Quota-exceeded explanation card ──────────────────────────────────────────

const QUOTA_EXHAUSTED_RESULT = {
  valuation: {
    predicted_price: 1200000,
    market_price: 1250000,
    price_difference: -50000,
    price_difference_pct: -4.0,
    price_low: null,
    price_high: null,
    valuation_interval_note: null,
  },
  investment_analysis: {
    deal_label: 'Hold',
    investment_score: 60,
    confidence: 'Medium',
    recommendation: 'Hold',
    analysis_summary: 'Decent property.',
    roi_estimate: 4.5,
  },
  drivers: {
    top_drivers: ['Location'],
    global_context: ['Stable market'],
  },
  explanation: {
    summary: 'Daily AI explanation quota reached. Upgrade to a paid plan for more analyses.',
    opportunity: 'Daily AI explanation quota reached. Upgrade to a paid plan for more analyses.',
    risks: 'Daily AI explanation quota reached. Upgrade to a paid plan for more analyses.',
  },
  metadata: { model_version: 'v2' },
}

async function fillAndSubmitMinimalForm(user) {
  await user.selectOptions(screen.getByRole('combobox', { name: /borough/i }), 'Brooklyn')
  await user.type(screen.getByPlaceholderText(/neighborhood/i), 'Park Slope')
  await user.selectOptions(screen.getAllByRole('combobox')[1], '02 TWO FAMILY DWELLINGS')
  await user.type(screen.getByPlaceholderText(/e\.g\. 1925|year/i), '1925')
  await user.type(screen.getByPlaceholderText(/e\.g\. 2000|gross sq/i), '2000')
  await user.type(screen.getByPlaceholderText(/e\.g\. 1500|land sq/i), '1500')
  await user.type(screen.getByPlaceholderText(/40\./), '40.6720')
  await user.type(screen.getByPlaceholderText(/-73\./), '-73.9778')
  await user.type(screen.getByPlaceholderText(/1250000|market price/i), '1250000')
  await user.click(screen.getByRole('button', { name: /Run Analysis/i }))
}

describe('Analyze page — quota-exceeded explanation card', () => {
  it('renders upgrade card instead of explanation panels when backend returns quota text', async () => {
    mockAnalyzeProperty.mockResolvedValueOnce(QUOTA_EXHAUSTED_RESULT)
    renderAnalyze({ daily_limit: 10, used_today: 10, remaining: 0 })
    const user = userEvent.setup()

    // Click the Brooklyn preset button to fill all form fields instantly
    const brooklynBtn = screen.getAllByRole('button').find(
      (b) => b.textContent.trim() === 'Brooklyn'
    )
    expect(brooklynBtn).toBeTruthy()
    await user.click(brooklynBtn)

    await user.click(screen.getByRole('button', { name: /Run Analysis/i }))

    // The quota-exhausted explanation card has a unique CTA
    await waitFor(() =>
      expect(screen.getByText(/Upgrade on Profile page/i)).toBeInTheDocument()
    )
    // The three normal explanation boxes should NOT be visible
    expect(screen.queryByText(/^Summary$|^Opportunity$|^Risks$/)).toBeNull()
  })
})

// ── Form validation ───────────────────────────────────────────────────────────

describe('Analyze page — form validation', () => {
  it('shows borough validation error when submitted empty', async () => {
    renderAnalyze()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Run Analysis/i }))
    await waitFor(() =>
      expect(screen.getByText(/Borough is required/i)).toBeInTheDocument()
    )
  })
})
