import { useEffect, useRef } from 'react'
import 'mapbox-gl/dist/mapbox-gl.css'

let mapboxgl = null
async function getMapboxGL() {
  if (mapboxgl) return mapboxgl
  const mod = await import('mapbox-gl')
  mapboxgl = mod.default
  return mapboxgl
}

const MICRO_MOVE_DEG = 0.00008
const LARGE_JUMP_DEG = 0.003

const DEFAULT_STYLE = 'mapbox://styles/mapbox/standard'

/**
 * Interactive preview map for geocoded coordinates.
 *
 * @param {{ lat: number, lng: number, onCoordinatesChange?: (lat: number, lng: number) => void }} props
 */
export default function PropertyLocationMap({ lat, lng, onCoordinatesChange }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)
  const prevLngLatRef = useRef(null)
  const onCoordinatesChangeRef = useRef(onCoordinatesChange)
  onCoordinatesChangeRef.current = onCoordinatesChange

  const token = import.meta.env.VITE_MAPBOX_TOKEN
  const mapStyle = import.meta.env.VITE_MAPBOX_STYLE || DEFAULT_STYLE

  const hasCoords = lat != null && lng != null

  // Create map once while coords exist; deps use `hasCoords` only so lat/lng tweaks do not destroy the map.
  useEffect(() => {
    if (!token || !hasCoords) {
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
        markerRef.current = null
        prevLngLatRef.current = null
      }
      return undefined
    }

    if (mapRef.current) return undefined

    let cancelled = false

    getMapboxGL().then((mgl) => {
      if (cancelled || !containerRef.current) return

      mgl.accessToken = token

      const map = new mgl.Map({
        container: containerRef.current,
        style: mapStyle,
        center: [lng, lat],
        zoom: 16,
        pitch: 52,
        bearing: -17,
        maxPitch: 85,
        interactive: true,
        dragRotate: true,
        touchPitch: true,
        attributionControl: false,
      })

      map.addControl(new mgl.NavigationControl({ visualizePitch: true }), 'top-right')
      map.addControl(new mgl.ScaleControl({ maxWidth: 100, unit: 'imperial' }), 'bottom-left')
      map.addControl(new mgl.FullscreenControl(), 'top-right')
      map.addControl(new mgl.AttributionControl({ compact: true }), 'bottom-right')

      const draggable = typeof onCoordinatesChangeRef.current === 'function'

      const marker = new mgl.Marker({
        color: '#06b6d4',
        draggable,
      })
        .setLngLat([lng, lat])
        .addTo(map)

      marker.on('dragend', () => {
        const cb = onCoordinatesChangeRef.current
        if (!cb) return
        const ll = marker.getLngLat()
        cb(ll.lat, ll.lng)
      })

      markerRef.current = marker
      mapRef.current = map
      prevLngLatRef.current = [lng, lat]
    })

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
        markerRef.current = null
        prevLngLatRef.current = null
      }
    }
    // lat/lng updates are handled by the following effect; `hasCoords` only toggles map mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, hasCoords, mapStyle])

  // Recentre when coordinates change (geocode / preset / drag sync).
  useEffect(() => {
    if (!mapRef.current || lat == null || lng == null) return

    const map = mapRef.current
    const center = [lng, lat]
    const prev = prevLngLatRef.current

    markerRef.current?.setLngLat(center)

    if (!prev) {
      prevLngLatRef.current = center
      return
    }

    const dist = Math.hypot(center[0] - prev[0], center[1] - prev[1])

    if (dist < MICRO_MOVE_DEG) {
      prevLngLatRef.current = center
      return
    }

    prevLngLatRef.current = center

    if (dist < LARGE_JUMP_DEG) {
      map.easeTo({ center, duration: 280 })
      return
    }

    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduced) {
      map.jumpTo({ center })
      return
    }

    map.flyTo({
      center,
      zoom: Math.max(map.getZoom(), 15),
      pitch: map.getPitch() || 52,
      bearing: map.getBearing(),
      duration: 1600,
      essential: true,
    })
  }, [lat, lng])

  if (!token || lat == null || lng == null) return null

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      <div ref={containerRef} className="h-[min(52vw,320px)] min-h-[240px] w-full" />
      <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-50 px-3 py-1.5 dark:bg-slate-900">
        <p className="text-[10px] leading-tight text-slate-400 dark:text-slate-500">
          {onCoordinatesChange
            ? 'Drag the pin to fine-tune coordinates. Pan, zoom, and tilt the map — not a surveyed boundary.'
            : 'Pan, zoom, and tilt the map. Pin shows approximate geocoded location.'}
        </p>
      </div>
    </div>
  )
}
