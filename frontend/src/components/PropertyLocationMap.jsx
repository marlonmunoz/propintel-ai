import { useEffect, useRef, useState } from 'react'
import 'mapbox-gl/dist/mapbox-gl.css'
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

const DEFAULT_STYLE = 'mapbox://styles/mapbox/standard'

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
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)
  const prevLngLatRef = useRef(null)
  const subwayGeoRef = useRef(null)
  const onCoordinatesChangeRef = useRef(onCoordinatesChange)
  onCoordinatesChangeRef.current = onCoordinatesChange

  const [nearestSubway, setNearestSubway] = useState(null)
  const [subwayLoadError, setSubwayLoadError] = useState(false)

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
        subwayGeoRef.current = null
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

      map.on('load', () => {
        if (cancelled) return
        addSubwayLayers(map)
        loadSubwayStationsGeoJson()
          .then((geojson) => {
            if (cancelled || !mapRef.current) return
            subwayGeoRef.current = geojson
            map.getSource('subway-stations')?.setData(geojson)
            const label = updateNearestSubwayOverlay(map, geojson, lat, lng)
            setNearestSubway(label)
            setSubwayLoadError(false)
          })
          .catch(() => {
            if (!cancelled) setSubwayLoadError(true)
          })
      })
    })

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
        markerRef.current = null
        prevLngLatRef.current = null
        subwayGeoRef.current = null
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

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      <div ref={containerRef} className="h-[min(52vw,320px)] min-h-[240px] w-full" />
      <div className="flex flex-col gap-1 bg-slate-50 px-3 py-2 dark:bg-slate-900">
        <p className="text-[10px] leading-tight text-slate-500 dark:text-slate-500">
          {onCoordinatesChange
            ? 'Drag the pin to fine-tune coordinates. Cyan dots are NYC subway stops.'
            : 'Cyan dots are NYC subway stops. Pin shows approximate geocoded location.'}
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
