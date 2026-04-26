import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

// Mock Supabase so AuthContext doesn't try to connect.
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

// Mock fetchProfile — called by AuthContext on mount.
vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockRejectedValue(new Error('no session')),
}))

// Mock the Navbar (heavy component with many deps) to isolate the page.
vi.mock('../../components/Navbar', () => ({
  default: () => <nav data-testid="navbar" />,
}))

import Home from '../../pages/Home'
import { AuthProvider } from '../../context/AuthContext'

function renderHome() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter>
          <Home />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

describe('Home page', () => {
  it('renders the hero heading', () => {
    renderHome()
    expect(
      screen.getByRole('heading', {
        name: /Buy, hold, or sell—with NYC sales data behind your instinct/i,
      })
    ).toBeInTheDocument()
  })

  it('renders consolidated hero copy (dual audience and crystal ball)', () => {
    renderHome()
    expect(screen.getByText(/buying a home or sizing an investment/i)).toBeInTheDocument()
    expect(screen.getByText(/not a crystal ball/i)).toBeInTheDocument()
  })

  it('renders the "Analyze Property" CTA link', () => {
    renderHome()
    expect(screen.getByRole('link', { name: /Analyze Property/i })).toBeInTheDocument()
  })

  it('renders the "Model performance" section heading', () => {
    renderHome()
    expect(screen.getByText(/Built on real NYC sales/i)).toBeInTheDocument()
  })

  it('renders all three metric labels', () => {
    renderHome()
    expect(screen.getByText(/Strongest segment/i)).toBeInTheDocument()
    // Exact match to avoid collisions with feature description text.
    expect(screen.getByText(/^2-family homes$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Segment models$/i)).toBeInTheDocument()
  })

  it('renders the "Product" section', () => {
    renderHome()
    expect(screen.getByText(/What You Get/i)).toBeInTheDocument()
  })

  it('renders the Footer disclaimer', () => {
    renderHome()
    const footer = screen.getByRole('contentinfo')
    expect(
      within(footer).getByText(/not financial, legal, or investment advice/i)
    ).toBeInTheDocument()
  })
})
