import { useCallback, useEffect, useRef, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useTheme } from '../context/ThemeContext'
import {
  findNearestSubwayStation,
  formatSubwayDistance,
  loadSubwayStationsGeoJson,
} from '../utils/subwayStations'

let mapboxgl = null
async function getMapboxGL() {
  if (mapboxgl) return mapboxgl
  const mod = await import('mapbox-gl')
  mapboxgl = mod.default
  return mapboxgl
}

const MICRO_MOVE_DEG = 0.00008
const LARGE_JUMP_DEG = 0.003
const MAP_APPEARANCE_KEY = 'propintel-map-appearance'

const DAY_STYLE =
  import.meta.env.VITE_MAPBOX_STYLE_DAY ||
  import.meta.env.VITE_MAPBOX_STYLE ||
  'mapbox://styles/mapbox/standard'
const NIGHT_STYLE =
  import.meta.env.VITE_MAPBOX_STYLE_NIGHT || 'mapbox://styles/mapbox/dark-v11'

function readStoredMapAppearance(fallback) {
  if (typeof window === 'undefined') return fallback
  const saved = window.localStorage.getItem(MAP_APPEARANCE_KEY)
  if (saved === 'day' || saved === 'night') return saved
  return fallback
}

function supportsLightPreset(map) {
  try {
    return map.getConfigProperty('basemap', 'lightPreset') !== undefined
  } catch {
    return false
  }
}

function addSubwayLayers(map) {
  if (map.getSource('subway-stations')) return

  map.addSource('subway-nearest-line', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  map.addLayer({
    id: 'subway-walk-line',
    type: 'line',
    source: 'subway-nearest-line',
    paint: {
      'line-color': '#06b6d4',
      'line-width': 2,
      'line-dasharray': [2, 2],
      'line-opacity': 0.85,
    },
  })

  map.addSource('subway-stations', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  map.addLayer({
    id: 'subway-stations-circle',
    type: 'circle',
    source: 'subway-stations',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 2, 15, 3.5, 17, 5],
      'circle-color': '#0e7490',
      'circle-opacity': 0.6,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#f8fafc',
      'circle-stroke-opacity': 0.85,
    },
  })

  map.addSource('subway-nearest-point', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  map.addLayer({
    id: 'subway-nearest-circle',
    type: 'circle',
    source: 'subway-nearest-point',
    paint: {
      'circle-radius': 7,
      'circle-color': '#06b6d4',
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
    },
  })
}

function setSubwayPaintForAppearance(map, appearance) {
  if (!map.getLayer('subway-stations-circle')) return
  const isNight = appearance === 'night'
  map.setPaintProperty('subway-stations-circle', 'circle-color', isNight ? '#22d3ee' : '#0e7490')
  map.setPaintProperty('subway-stations-circle', 'circle-stroke-color', isNight ? '#0f172a' : '#f8fafc')
}

function updateNearestSubwayOverlay(map, geojson, lat, lng) {
  const nearest = findNearestSubwayStation(geojson, lat, lng)
  if (!nearest) return null

  const { feature, km } = nearest
  const [stationLng, stationLat] = feature.geometry.coordinates

  map.getSource('subway-nearest-line')?.setData({
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates: [
        [lng, lat],
        [stationLng, stationLat],
      ],
    },
  })
  map.getSource('subway-nearest-point')?.setData({
    type: 'FeatureCollection',
    features: [feature],
  })

  const name = feature.properties?.name ?? 'Subway'
  const lines = feature.properties?.lines
  const lineSuffix = lines ? ` (${lines})` : ''
  return `${name}${lineSuffix} · ${formatSubwayDistance(km)}`
}

/**
 * Interactive preview map for geocoded coordinates.
 *
 * @param {{ lat: number, lng: number, onCoordinatesChange?: (lat: number, lng: number) => void }} props
 */
export default function PropertyLocationMap({ lat, lng, onCoordinatesChange }) {
  const { theme } = useTheme()
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)
  const prevLngLatRef = useRef(null)
  const subwayGeoRef = useRef(null)
  const mapAppearanceRef = useRef('day')
  const coordsRef = useRef({ lat, lng })
  const onCoordinatesChangeRef = useRef(onCoordinatesChange)
  onCoordinatesChangeRef.current = onCoordinatesChange
  coordsRef.current = { lat, lng }

  const [nearestSubway, setNearestSubway] = useState(null)
  const [subwayLoadError, setSubwayLoadError] = useState(false)
  const [mapAppearance, setMapAppearance] = useState(() =>
    readStoredMapAppearance(theme === 'dark' ? 'night' : 'day')
  )

  mapAppearanceRef.current = mapAppearance

  const token = import.meta.env.VITE_MAPBOX_TOKEN
  const hasCoords = lat != null && lng != null

  const syncSubwayData = useCallback((map) => {
    const { lat: cLat, lng: cLng } = coordsRef.current
    if (cLat == null || cLng == null) return

    const apply = (geojson) => {
      subwayGeoRef.current = geojson
      map.getSource('subway-stations')?.setData(geojson)
      const label = updateNearestSubwayOverlay(map, geojson, cLat, cLng)
      setNearestSubway(label)
      setSubwayLoadError(false)
    }

    if (subwayGeoRef.current) {
      apply(subwayGeoRef.current)
      return
    }

    loadSubwayStationsGeoJson()
      .then(apply)
      .catch(() => setSubwayLoadError(true))
  }, [])

  const onStyleReady = useCallback(
    (map) => {
      if (supportsLightPreset(map)) {
        map.setConfigProperty(
          'basemap',
          'lightPreset',
          mapAppearanceRef.current === 'night' ? 'night' : 'day'
        )
      } else if (mapAppearanceRef.current === 'night') {
        map.setStyle(NIGHT_STYLE)
        return
      }

      addSubwayLayers(map)
      setSubwayPaintForAppearance(map, mapAppearanceRef.current)
      syncSubwayData(map)
    },
    [syncSubwayData]
  )

  const applyMapAppearance = useCallback(
    (map, appearance) => {
      if (supportsLightPreset(map)) {
        map.setConfigProperty('basemap', 'lightPreset', appearance === 'night' ? 'night' : 'day')
        setSubwayPaintForAppearance(map, appearance)
        return
      }

      map.setStyle(appearance === 'night' ? NIGHT_STYLE : DAY_STYLE)
    },
    []
  )

  const toggleMapAppearance = useCallback(() => {
    setMapAppearance((prev) => {
      const next = prev === 'night' ? 'day' : 'night'
      window.localStorage.setItem(MAP_APPEARANCE_KEY, next)
      mapAppearanceRef.current = next

      const map = mapRef.current
      if (map) applyMapAppearance(map, next)

      return next
    })
  }, [applyMapAppearance])

  // Create map once while coords exist.
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
        style: DAY_STYLE,
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

      map.on('style.load', () => {
        if (!cancelled) onStyleReady(map)
      })
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, hasCoords])

  // Recentre when coordinates change (geocode / preset / drag sync).
  useEffect(() => {
    if (!mapRef.current || lat == null || lng == null) return

    const map = mapRef.current
    const center = [lng, lat]
    const prev = prevLngLatRef.current

    markerRef.current?.setLngLat(center)

    if (subwayGeoRef.current && map.getSource('subway-stations')) {
      const label = updateNearestSubwayOverlay(map, subwayGeoRef.current, lat, lng)
      setNearestSubway(label)
    }

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

  const isNightMap = mapAppearance === 'night'

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      <div className="relative">
        <div ref={containerRef} className="h-[min(52vw,320px)] min-h-[240px] w-full" />
        <button
          type="button"
          onClick={toggleMapAppearance}
          className={[
            'absolute left-2 top-2 z-10 flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5',
            'text-xs font-semibold shadow-md backdrop-blur-sm transition',
            'border-slate-200/90 bg-white/95 text-slate-800 hover:bg-white',
            'dark:border-slate-600/80 dark:bg-slate-900/90 dark:text-slate-100 dark:hover:bg-slate-800',
          ].join(' ')}
          aria-pressed={isNightMap}
          aria-label={isNightMap ? 'Switch map to day mode' : 'Switch map to night mode'}
          title={isNightMap ? 'Day map' : 'Night map'}
        >
          {isNightMap ? (
            <>
              <Sun className="h-3.5 w-3.5 text-amber-500" aria-hidden />
              Day
            </>
          ) : (
            <>
              <Moon className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden />
              Night
            </>
          )}
        </button>
      </div>
      <div className="flex flex-col gap-1 bg-slate-50 px-3 py-2 dark:bg-slate-900">
        <p className="text-[10px] leading-tight text-slate-500 dark:text-slate-500">
          {onCoordinatesChange
            ? 'Drag the pin to fine-tune coordinates. Cyan dots are NYC subway stops.'
            : 'Cyan dots are NYC subway stops. Pin shows approximate geocoded location.'}
          {' '}
          Map day/night is independent of site theme.
        </p>
        {nearestSubway ? (
          <p className="text-[10px] font-medium leading-tight text-cyan-800 dark:text-cyan-400">
            Nearest subway: {nearestSubway}
          </p>
        ) : null}
        {subwayLoadError ? (
          <p className="text-[10px] leading-tight text-amber-700 dark:text-amber-400">
            Subway stops could not be loaded.
          </p>
        ) : null}
      </div>
    </div>
  )
}
