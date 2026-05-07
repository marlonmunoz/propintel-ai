import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../../components/Navbar', () => ({
  default: () => <nav data-testid="navbar" />,
}))

import Contact from '../../pages/Contact'

function renderContact() {
  return render(
    <MemoryRouter>
      <Contact />
    </MemoryRouter>
  )
}

describe('Contact page', () => {
  it('renders the page heading', () => {
    renderContact()
    expect(screen.getByRole('heading', { name: /how can we help/i })).toBeInTheDocument()
  })

  it('exposes a customer support mailto with subject', () => {
    renderContact()
    const supportLink = screen.getByRole('link', { name: /email support@propintel-ai\.com/i })
    expect(supportLink.getAttribute('href')).toContain('mailto:support@propintel-ai.com')
    expect(supportLink.getAttribute('href')).toContain('subject=')
  })

  it('exposes a partnerships / press mailto for marlon@', () => {
    renderContact()
    const partnerLink = screen.getByRole('link', { name: /email marlon@propintel-ai\.com/i })
    expect(partnerLink.getAttribute('href')).toContain('mailto:marlon@propintel-ai.com')
    expect(partnerLink.getAttribute('href')).toContain('subject=')
  })

  it('describes the two distinct lanes', () => {
    renderContact()
    expect(screen.getByRole('heading', { name: /customer support/i })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /press, partnerships & investors/i })
    ).toBeInTheDocument()
  })
})
