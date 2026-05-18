import { describe, it, expect } from 'vitest'
import { findNearestSubwayStation, formatSubwayDistance, haversineKm } from '../../utils/subwayStations'

const sampleCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-73.987495, 40.75529] },
      properties: { name: 'Times Sq-42 St', lines: '1 2 3' },
    },
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-73.95, 40.68] },
      properties: { name: 'Franklin Av', lines: 'S' },
    },
  ],
}

describe('subwayStations utils', () => {
  it('haversineKm returns plausible NYC distance', () => {
    const km = haversineKm(40.75529, -73.987495, 40.68, -73.95)
    expect(km).toBeGreaterThan(5)
    expect(km).toBeLessThan(15)
  })

  it('findNearestSubwayStation picks closest stop', () => {
    const nearTimesSq = findNearestSubwayStation(sampleCollection, 40.756, -73.988)
    expect(nearTimesSq.feature.properties.name).toBe('Times Sq-42 St')

    const nearFranklin = findNearestSubwayStation(sampleCollection, 40.681, -73.956)
    expect(nearFranklin.feature.properties.name).toBe('Franklin Av')
  })

  it('formatSubwayDistance uses meters under 1 km', () => {
    expect(formatSubwayDistance(0.24)).toMatch(/m$/)
    expect(formatSubwayDistance(1.4)).toMatch(/km$/)
  })
})
