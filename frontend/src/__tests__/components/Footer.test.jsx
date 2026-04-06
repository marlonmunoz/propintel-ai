import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Footer from '../../components/Footer'

describe('Footer', () => {
  it('renders the current year', () => {
    render(<Footer />)
    const year = new Date().getFullYear().toString()
    expect(screen.getByText(new RegExp(year))).toBeInTheDocument()
  })

  it('renders the PropIntel AI brand name', () => {
    render(<Footer />)
    expect(screen.getByText(/PropIntel AI/i)).toBeInTheDocument()
  })

  it('renders the disclaimer text', () => {
    render(<Footer />)
    expect(
      screen.getByText(/not financial, legal, or investment advice/i)
    ).toBeInTheDocument()
  })

  it('uses a <footer> element', () => {
    const { container } = render(<Footer />)
    expect(container.querySelector('footer')).toBeInTheDocument()
  })
})
