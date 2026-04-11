import { useEffect, useRef } from 'react'
import 'mapbox-gl/dist/mapbox-gl.css'

// JS bundle is loaded dynamically so it doesn't block initial page paint.
// The CSS above is static — Vite handles it at build time without extra weight.
let mapboxgl = null
async function getMapboxGL() {
  if (mapboxgl) return mapboxgl
  const mod = await import('mapbox-gl')
  mapboxgl = mod.default
  return mapboxgl
}

export default function PropertyLocationMap({ lat, lng }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)

  const token = import.meta.env.VITE_MAPBOX_TOKEN

  // Init effect: runs whenever lat/lng change, but only creates the map once.
  // Dependency array includes lat+lng so the effect re-evaluates when coordinates
  // first arrive from the geocode pick (on mount they are null, so init is skipped).
  useEffect(() => {
    if (!token || !lat || !lng) return
    if (mapRef.current) return // already initialised — update effect handles moves

    let cancelled = false

    getMapboxGL().then((mgl) => {
      if (cancelled || !containerRef.current) return

      mgl.accessToken = token

      const map = new mgl.Map({
        container: containerRef.current,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [lng, lat],
        zoom: 15,
        interactive: false,
        attributionControl: false,
      })

      map.addControl(
        new mgl.AttributionControl({ compact: true }),
        'bottom-right',
      )

      markerRef.current = new mgl.Marker({ color: '#06b6d4' })
        .setLngLat([lng, lat])
        .addTo(map)

      mapRef.current = map
    })

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
        markerRef.current = null
      }
    }
  }, [token, lat, lng])

  // Update effect: recentres map + moves marker on subsequent coordinate changes.
  useEffect(() => {
    if (!mapRef.current || !lat || !lng) return
    mapRef.current.setCenter([lng, lat])
    markerRef.current?.setLngLat([lng, lat])
  }, [lat, lng])

  if (!token || !lat || !lng) return null

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      <div ref={containerRef} style={{ height: 240 }} />
      <p className="bg-slate-50 px-3 py-1.5 text-[10px] leading-tight text-slate-400 dark:bg-slate-900 dark:text-slate-500">
        Pin shows the approximate geocoded location, not a surveyed boundary.
      </p>
    </div>
  )
}
