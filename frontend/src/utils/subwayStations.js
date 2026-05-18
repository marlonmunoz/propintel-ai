const EARTH_RADIUS_KM = 6371

/** @param {number} lat1 @param {number} lng1 @param {number} lat2 @param {number} lng2 */
export function haversineKm(lat1, lng1, lat2, lng2) {
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(a))
}

let geoJsonPromise = null

/** NYC subway stops (MTA GTFS-derived). Static asset — same source as ML `subway_dist_km`. */
export function loadSubwayStationsGeoJson() {
  if (!geoJsonPromise) {
    geoJsonPromise = fetch('/data/nyc_subway_stations.geojson')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load subway stations')
        return res.json()
      })
      .catch((err) => {
        geoJsonPromise = null
        throw err
      })
  }
  return geoJsonPromise
}

/**
 * @param {import('geojson').FeatureCollection} collection
 * @param {number} lat
 * @param {number} lng
 */
export function findNearestSubwayStation(collection, lat, lng) {
  if (!collection?.features?.length) return null

  let best = null
  let bestKm = Infinity

  for (const feature of collection.features) {
    const [flng, flat] = feature.geometry?.coordinates ?? []
    if (flat == null || flng == null) continue
    const km = haversineKm(lat, lng, flat, flng)
    if (km < bestKm) {
      bestKm = km
      best = { feature, km }
    }
  }

  return best
}

/** @param {number} km */
export function formatSubwayDistance(km) {
  if (km == null || Number.isNaN(km)) return ''
  if (km < 1) return `${Math.round(km * 1000)} m`
  return `${km.toFixed(2)} km`
}
