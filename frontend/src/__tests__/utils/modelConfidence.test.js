import { describe, it, expect } from 'vitest'
import { modelConfidenceBadgeClasses, modelConfidenceCalloutClasses } from '../../utils/modelConfidence'

describe('modelConfidence utils', () => {
  it('returns emerald classes for high tier', () => {
    expect(modelConfidenceBadgeClasses('high')).toContain('emerald')
  })

  it('returns amber classes for directional tier', () => {
    expect(modelConfidenceBadgeClasses('directional')).toContain('amber')
  })

  it('returns slate classes for fallback tier', () => {
    expect(modelConfidenceCalloutClasses('fallback')).toContain('slate')
  })
})
