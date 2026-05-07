import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SupportLink, { SUPPORT_EMAIL } from '../../components/SupportLink'

describe('SupportLink', () => {
  it('exposes the canonical support email constant', () => {
    expect(SUPPORT_EMAIL).toBe('support@propintel-ai.com')
  })

  it('renders the email as visible text by default', () => {
    render(<SupportLink />)
    const link = screen.getByRole('link', { name: SUPPORT_EMAIL })
    expect(link).toHaveAttribute('href', `mailto:${SUPPORT_EMAIL}`)
  })

  it('uses custom children as the link label', () => {
    render(<SupportLink>Contact support</SupportLink>)
    expect(screen.getByRole('link', { name: /contact support/i })).toBeInTheDocument()
  })

  it('includes a URL-encoded subject when provided', () => {
    render(<SupportLink subject="Account deletion request">support</SupportLink>)
    const link = screen.getByRole('link', { name: /support/i })
    expect(link.getAttribute('href')).toBe(
      `mailto:${SUPPORT_EMAIL}?subject=Account%20deletion%20request`
    )
  })

  it('appends a body parameter alongside the subject', () => {
    render(
      <SupportLink subject="App error" body="What were you doing?">
        support
      </SupportLink>
    )
    const href = screen.getByRole('link', { name: /support/i }).getAttribute('href')
    expect(href).toContain(`mailto:${SUPPORT_EMAIL}?`)
    expect(href).toContain('subject=App%20error')
    expect(href).toContain('body=What%20were%20you%20doing%3F')
  })

  it('applies a custom className when provided', () => {
    render(<SupportLink className="custom-class">support</SupportLink>)
    expect(screen.getByRole('link', { name: /support/i })).toHaveClass('custom-class')
  })
})
