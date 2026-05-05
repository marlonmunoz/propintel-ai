import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Footer from '../../components/Footer'

function renderFooter() {
  return render(
    <MemoryRouter>
      <Footer />
    </MemoryRouter>
  )
}

describe('Footer', () => {
  it('renders the current year', () => {
    renderFooter()
    const year = new Date().getFullYear().toString()
    expect(screen.getByText(new RegExp(year))).toBeInTheDocument()
  })

  it('renders the PropIntel AI brand name', () => {
    renderFooter()
    expect(screen.getByText(/PropIntel AI/i)).toBeInTheDocument()
  })

  it('renders the disclaimer text', () => {
    renderFooter()
    expect(
      screen.getByText(/not financial, legal, tax, or investment advice/i)
    ).toBeInTheDocument()
  })

  it('links to legal pages', () => {
    renderFooter()
    const nav = screen.getByRole('navigation', { name: /legal/i })
    expect(nav).toBeInTheDocument()
    expect(nav.querySelector('a[href="/terms"]')).toBeTruthy()
    expect(nav.querySelector('a[href="/privacy"]')).toBeTruthy()
    expect(nav.querySelector('a[href="/disclaimer"]')).toBeTruthy()
  })

  it('uses a <footer> element', () => {
    const { container } = renderFooter()
    expect(container.querySelector('footer')).toBeInTheDocument()
  })
})
