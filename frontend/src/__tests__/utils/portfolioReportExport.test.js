import { describe, it, expect } from 'vitest'
import { buildPropertyCsv } from '../../utils/portfolioReportExport'

describe('buildPropertyCsv', () => {
  it('outputs a header row and one data row', () => {
    const property = {
      id: 42,
      address: '123 Main St',
      zipcode: '10001',
      bedrooms: 2,
      bathrooms: 1,
      sqft: 900,
      listing_price: 750000,
      created_at: '2026-01-15T12:00:00Z',
      analysis: {
        valuation: {
          predicted_price: 800000,
          market_price: 780000,
          price_difference_pct: 2.5,
        },
        investment_analysis: {
          deal_label: 'Buy',
          investment_score: 72,
          roi_estimate: 5.1,
          recommendation: 'Strong fundamentals.',
          analysis_summary: 'Summary line.',
        },
      },
    }
    const [header, row] = buildPropertyCsv(property).split('\r\n')
    expect(header.startsWith('property_id,')).toBe(true)
    expect(row).toContain('123 Main St')
    expect(row).toContain('Buy')
    expect(row).toContain('800000')
  })

  it('escapes commas and quotes in text fields', () => {
    const property = {
      id: 1,
      address: '45 W 34th St, Apt 2',
      zipcode: '10001',
      bedrooms: 1,
      bathrooms: 1,
      sqft: 500,
      listing_price: 100,
      analysis: {
        investment_analysis: {
          recommendation: 'Say "yes" to this deal',
          analysis_summary: 'ok',
        },
      },
    }
    const csv = buildPropertyCsv(property)
    expect(csv).toContain('"45 W 34th St, Apt 2"')
    expect(csv).toContain('""yes""')
  })
})
