import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ModelConfidenceBadge from '../../components/ModelConfidenceBadge'
import ModelConfidenceCallout from '../../components/ModelConfidenceCallout'

const HIGH_METADATA = {
  segment: 'one_family',
  segment_label: 'One-family',
  model_confidence_tier: 'high',
  model_confidence_label: 'High confidence',
  model_confidence_note: 'Strong segment model.',
}

const DIRECTIONAL_METADATA = {
  segment: 'coop',
  segment_label: 'Co-op',
  model_confidence_tier: 'directional',
  model_confidence_label: 'Directional estimate',
  model_confidence_note: 'Weaker public data for co-ops.',
}

describe('ModelConfidenceBadge', () => {
  it('renders the confidence label', () => {
    render(<ModelConfidenceBadge metadata={HIGH_METADATA} />)
    expect(screen.getByText('High confidence')).toBeInTheDocument()
  })

  it('renders nothing when metadata is incomplete', () => {
    const { container } = render(<ModelConfidenceBadge metadata={{}} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('ModelConfidenceCallout', () => {
  it('renders segment label and explanatory note', () => {
    render(<ModelConfidenceCallout metadata={DIRECTIONAL_METADATA} />)
    expect(screen.getByText(/Valuation confidence/i)).toBeInTheDocument()
    expect(screen.getByText(/Co-op model/i)).toBeInTheDocument()
    expect(screen.getByText(/Weaker public data for co-ops/i)).toBeInTheDocument()
  })
})
