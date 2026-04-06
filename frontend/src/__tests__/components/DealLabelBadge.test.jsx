import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DealLabelBadge, { dealLabelBadgeClasses } from '../../components/DealLabelBadge'

// --- Pure function unit tests ---

describe('dealLabelBadgeClasses()', () => {
  it('returns emerald classes for "buy"', () => {
    expect(dealLabelBadgeClasses('buy')).toMatch(/emerald/)
  })

  it('is case-insensitive for "Buy"', () => {
    expect(dealLabelBadgeClasses('Buy')).toMatch(/emerald/)
  })

  it('returns amber classes for "hold"', () => {
    expect(dealLabelBadgeClasses('hold')).toMatch(/amber/)
  })

  it('returns rose classes for "avoid"', () => {
    expect(dealLabelBadgeClasses('Avoid')).toMatch(/rose/)
  })

  it('returns rose (default) classes for unknown label', () => {
    expect(dealLabelBadgeClasses('unknown')).toMatch(/rose/)
  })

  it('returns rose (default) classes for null/undefined', () => {
    expect(dealLabelBadgeClasses(null)).toMatch(/rose/)
    expect(dealLabelBadgeClasses(undefined)).toMatch(/rose/)
  })
})

// --- Component render tests ---

describe('DealLabelBadge component', () => {
  it('renders nothing when label is falsy', () => {
    const { container } = render(<DealLabelBadge label={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders the label text', () => {
    render(<DealLabelBadge label="Buy" />)
    expect(screen.getByText('Buy')).toBeInTheDocument()
  })

  it('renders as an inline <span>', () => {
    const { container } = render(<DealLabelBadge label="Hold" />)
    expect(container.querySelector('span')).toBeInTheDocument()
  })

  it('applies smaller classes when size="sm"', () => {
    const { container } = render(<DealLabelBadge label="Avoid" size="sm" />)
    const span = container.querySelector('span')
    expect(span.className).toMatch(/text-xs/)
  })

  it('applies larger classes for default size', () => {
    const { container } = render(<DealLabelBadge label="Avoid" />)
    const span = container.querySelector('span')
    expect(span.className).toMatch(/text-sm/)
  })
})
