import { useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion'
import { dealLabelBadgeClasses } from '../utils/dealLabelBadge'

/** Snapshot labels — align with `modelMetrics` on Home.jsx when you retrain. */
const HERO_METRICS = [
  { label: 'R² 0.83 · condo' },
  { label: '6 segments' },
  { label: 'XGBoost' },
  { label: 'R² 0.77 · 1-family' },
  { label: 'Buy', dealLabel: 'Buy' },
  { label: 'Hold', dealLabel: 'Hold' },
  { label: 'Avoid', dealLabel: 'Avoid' },
  { label: 'NYC comps' },
  { label: 'Inference' },
]

/** Comp nodes in % viewBox — lines converge on building center. */
const COMP_NODES = [
  { x: 13, y: 30, linkClass: 'hero-comp-link-0', nodeClass: 'hero-comp-node-0' },
  { x: 87, y: 24, linkClass: 'hero-comp-link-1', nodeClass: 'hero-comp-node-1' },
  { x: 9, y: 56, linkClass: 'hero-comp-link-2', nodeClass: 'hero-comp-node-2' },
  { x: 91, y: 60, linkClass: 'hero-comp-link-3', nodeClass: 'hero-comp-node-3' },
  { x: 20, y: 80, linkClass: 'hero-comp-link-4', nodeClass: 'hero-comp-node-4' },
  { x: 80, y: 76, linkClass: 'hero-comp-link-5', nodeClass: 'hero-comp-node-5' },
]

const BUILDING_CENTER = { x: 50, y: 54 }

const BOROUGHS = ['Manhattan', 'Brooklyn']
const BOROUGH_CYCLE_MS = 4500

const TAG_SLOTS = [
  { className: 'left-[8%] top-[14%]', offset: 0 },
  { className: 'right-[6%] top-[22%]', offset: 1 },
  { className: 'left-[14%] bottom-[18%]', offset: 2 },
]

const TAG_CYCLE_MS = 3200

function RotatingMetricTags({ reducedMotion }) {
  const [cycle, setCycle] = useState(0)
  const count = HERO_METRICS.length

  useEffect(() => {
    if (reducedMotion) return undefined
    const id = window.setInterval(() => {
      setCycle((c) => (c + 1) % count)
    }, TAG_CYCLE_MS)
    return () => window.clearInterval(id)
  }, [reducedMotion, count])

  return TAG_SLOTS.map((slot) => {
    const metric = HERO_METRICS[(cycle + slot.offset) % count]
    const isDeal = Boolean(metric.dealLabel)
    const tagKey = reducedMotion ? slot.className : `${metric.label}-${metric.dealLabel ?? ''}`

    return (
      <span
        key={slot.className}
        className={[
          'absolute rounded-full border px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wide',
          isDeal
            ? dealLabelBadgeClasses(metric.dealLabel)
            : [
                'border-cyan-700/35 bg-white text-cyan-900',
                'shadow-md shadow-slate-300/50',
                'dark:border-cyan-500/25 dark:bg-slate-950/70 dark:text-cyan-300 dark:shadow-sm',
              ].join(' '),
          slot.className,
          !reducedMotion && 'hero-tag-float',
        ]
          .filter(Boolean)
          .join(' ')}
        style={{ animationDelay: `${slot.offset * 0.4}s` }}
      >
        <span key={tagKey} className={!reducedMotion ? 'hero-tag-content-in' : undefined}>
          {metric.label}
        </span>
      </span>
    )
  })
}

function HudCorners() {
  const corners = [
    { key: 'tl', className: 'left-3 top-3 border-l border-t' },
    { key: 'tr', className: 'right-3 top-3 border-r border-t' },
    { key: 'bl', className: 'left-3 bottom-3 border-b border-l' },
    { key: 'br', className: 'right-3 bottom-3 border-b border-r' },
  ]

  return corners.map(({ key, className }) => (
    <span
      key={key}
      className={[
        'pointer-events-none absolute h-3.5 w-3.5 border-cyan-700/50 dark:border-cyan-400/25',
        className,
      ].join(' ')}
      aria-hidden
    />
  ))
}

function BoroughHint({ reducedMotion }) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (reducedMotion) return undefined
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % BOROUGHS.length)
    }, BOROUGH_CYCLE_MS)
    return () => window.clearInterval(id)
  }, [reducedMotion])

  const borough = reducedMotion ? 'Manhattan · Brooklyn' : BOROUGHS[index]

  return (
    <p
      className="pointer-events-none absolute bottom-3 right-3 z-[3] font-mono text-[9px] font-medium uppercase tracking-[0.18em] text-slate-500 dark:text-cyan-500/30"
      aria-hidden
    >
      <span key={borough} className={!reducedMotion ? 'hero-borough-fade' : undefined}>
        {borough}
      </span>
    </p>
  )
}

function HeroCtaRipple({ rippleKey, reducedMotion }) {
  if (!rippleKey || reducedMotion) return null

  return (
    <div
      key={rippleKey}
      className="pointer-events-none absolute inset-0 z-[5]"
      aria-hidden
    >
      <span className="hero-cta-ripple-beam" />
      <span className="hero-cta-ripple-ring" />
    </div>
  )
}

function CompGraph({ active }) {
  return (
    <svg
      className="hero-comp-graph pointer-events-none absolute inset-0 z-[2] h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden
    >
      <g fill="none" stroke="currentColor" strokeWidth="0.28" vectorEffect="non-scaling-stroke">
        {COMP_NODES.map((node) => (
          <line
            key={node.linkClass}
            x1={node.x}
            y1={node.y}
            x2={BUILDING_CENTER.x}
            y2={BUILDING_CENTER.y}
            className={[
              'hero-comp-link',
              active ? node.linkClass : 'hero-comp-link-static',
            ].join(' ')}
          />
        ))}
      </g>
      <g fill="currentColor">
        {COMP_NODES.map((node) => (
          <circle
            key={`dot-${node.linkClass}`}
            cx={node.x}
            cy={node.y}
            r="1.15"
            className={[
              'hero-comp-node',
              active ? node.nodeClass : 'hero-comp-node-static',
            ].join(' ')}
          />
        ))}
      </g>
    </svg>
  )
}

function ScanLine({ active }) {
  return (
    <div
      className="pointer-events-none absolute inset-0 z-[2] overflow-hidden"
      style={{
        maskImage:
          'radial-gradient(ellipse 55% 62% at 50% 54%, black 15%, transparent 72%)',
        WebkitMaskImage:
          'radial-gradient(ellipse 55% 62% at 50% 54%, black 15%, transparent 72%)',
      }}
      aria-hidden
    >
      <div
        className={[
          'hero-scan-line',
          active ? 'hero-scan-sweep' : 'hero-scan-static',
        ].join(' ')}
      />
      <div
        className={[
          'hero-scan-glow',
          active ? 'hero-scan-sweep hero-scan-glow-trail' : 'hero-scan-static',
        ].join(' ')}
      />
    </div>
  )
}

function IsometricBuilding({ scanActive }) {
  return (
    <svg
      viewBox="0 0 240 280"
      className="hero-building-svg h-full w-full max-h-[min(72vw,320px)] max-w-[min(72vw,280px)]"
      aria-hidden
    >
      <defs>
        <linearGradient id="hero-face-front" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" className="hero-building-face-front" />
          <stop offset="100%" className="hero-building-face-front" stopOpacity="0.06" />
        </linearGradient>
        <linearGradient id="hero-face-side" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" className="hero-building-face-side" />
          <stop offset="100%" className="hero-building-face-side" stopOpacity="0.04" />
        </linearGradient>
        <linearGradient id="hero-face-top" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" className="hero-building-face-top" />
          <stop offset="100%" className="hero-building-face-top" stopOpacity="0.12" />
        </linearGradient>
      </defs>

      <ellipse cx="120" cy="252" rx="72" ry="14" className="hero-building-shadow" />

      <g className="hero-building-stroke" fill="none" strokeWidth="1.35" strokeLinejoin="round">
        <path d="M48 168 L120 128 L192 168 L120 208 Z" fill="url(#hero-face-top)" />
        <path d="M48 168 L48 218 L120 258 L120 208 Z" fill="url(#hero-face-side)" />
        <path d="M120 208 L120 258 L192 218 L192 168 Z" fill="url(#hero-face-front)" />

        <path d="M62 118 L120 86 L178 118 L120 150 Z" fill="url(#hero-face-top)" opacity="0.95" />
        <path d="M62 118 L62 158 L120 190 L120 150 Z" fill="url(#hero-face-side)" opacity="0.95" />
        <path d="M120 150 L120 190 L178 158 L178 118 Z" fill="url(#hero-face-front)" opacity="0.95" />

        <path d="M76 72 L120 48 L164 72 L120 96 Z" fill="url(#hero-face-top)" />
        <path d="M76 72 L76 108 L120 132 L120 96 Z" fill="url(#hero-face-side)" />
        <path d="M120 96 L120 132 L164 108 L164 72 Z" fill="url(#hero-face-front)" />

        <path
          d="M88 148 L108 138 M88 162 L108 152"
          className={[
            'hero-building-windows',
            scanActive ? 'hero-window-glow' : undefined,
          ]
            .filter(Boolean)
            .join(' ')}
          strokeWidth="0.9"
        />
        <path
          d="M132 108 L148 100 M132 120 L148 112"
          className={[
            'hero-building-windows',
            scanActive ? 'hero-window-glow hero-window-glow-delay' : undefined,
          ]
            .filter(Boolean)
            .join(' ')}
          strokeWidth="0.9"
        />
        <path
          d="M128 176 L152 164 M128 192 L152 180"
          className={[
            'hero-building-windows',
            scanActive ? 'hero-window-glow hero-window-glow-delay-2' : undefined,
          ]
            .filter(Boolean)
            .join(' ')}
          strokeWidth="0.9"
        />
      </g>

      <g className="hero-building-signal" strokeWidth="1.1" fill="none">
        <path d="M24 80 Q 60 100 88 120" className="hero-signal-line" strokeDasharray="4 6" />
        <path
          d="M216 96 Q 180 112 152 128"
          className="hero-signal-line hero-signal-line-delay"
          strokeDasharray="4 6"
        />
        <path
          d="M200 220 Q 160 200 140 188"
          className="hero-signal-line hero-signal-line-delay-2"
          strokeDasharray="4 6"
        />
      </g>
    </svg>
  )
}

function ParticleField({ active }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!active) return undefined

    const canvas = canvasRef.current
    if (!canvas) return undefined

    const ctx = canvas.getContext('2d')
    if (!ctx) return undefined

    let rafId = 0
    let particles = []

    const resize = () => {
      const parent = canvas.parentElement
      if (!parent) return
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const { width, height } = parent.getBoundingClientRect()
      canvas.width = Math.max(1, Math.floor(width * dpr))
      canvas.height = Math.max(1, Math.floor(height * dpr))
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      const count = Math.min(48, Math.floor((width * height) / 9000))
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: 1 + Math.random() * 1.8,
        a: 0.15 + Math.random() * 0.45,
      }))
    }

    const tick = () => {
      const w = canvas.clientWidth
      const h = canvas.clientHeight
      ctx.clearRect(0, 0, w, h)

      const targetX = w / 2
      const targetY = h / 2 + h * 0.06

      for (const p of particles) {
        const dx = targetX - p.x
        const dy = targetY - p.y
        const dist = Math.hypot(dx, dy) || 1
        p.vx += (dx / dist) * 0.012
        p.vy += (dy / dist) * 0.012
        p.vx *= 0.98
        p.vy *= 0.98
        p.x += p.vx
        p.y += p.vy

        if (p.x < 0) p.x = w
        if (p.x > w) p.x = 0
        if (p.y < 0) p.y = h
        if (p.y > h) p.y = 0

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        const panel = canvas.closest('.hero-visual-panel')
        const accent = panel
          ? getComputedStyle(panel).getPropertyValue('--hero-accent').trim()
          : '14 116 144'
        const alpha = p.a * (document.documentElement.classList.contains('dark') ? 1 : 1.35)
        ctx.fillStyle = `rgba(${accent}, ${Math.min(alpha, 0.85)})`
        ctx.fill()
      }

      rafId = requestAnimationFrame(tick)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas.parentElement)
    rafId = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(rafId)
      ro.disconnect()
    }
  }, [active])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden
    />
  )
}

export default function HeroVisual({ ctaRippleKey = 0 }) {
  const reducedMotion = usePrefersReducedMotion()

  return (
    <div
      className="relative mx-auto w-full max-w-lg lg:mx-0 lg:max-w-none"
      aria-hidden
    >
      <div
        className={[
          'hero-visual-panel relative aspect-[5/4] w-full overflow-hidden rounded-2xl border',
          'border-cyan-200/70 bg-gradient-to-br from-cyan-50/80 via-slate-50 to-slate-100',
          'shadow-md shadow-slate-300/40',
          'dark:border-cyan-500/15 dark:from-transparent dark:via-transparent dark:to-transparent',
          'dark:bg-slate-900/40 dark:shadow-inner dark:shadow-cyan-500/5',
        ].join(' ')}
      >
        <div
          className={[
            'hero-visual-mesh pointer-events-none absolute inset-0',
            !reducedMotion && 'hero-mesh-drift',
          ]
            .filter(Boolean)
            .join(' ')}
        />

        <div className="hero-visual-grid pointer-events-none absolute inset-0 bg-[length:28px_28px] mask-[radial-gradient(ellipse_80%_70%_at_50%_55%,black_20%,transparent_75%)]" />

        <ParticleField active={!reducedMotion} />

        <div className="pointer-events-none absolute left-1/2 top-[54%] -translate-x-1/2 -translate-y-1/2">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className={[
                'hero-pulse-ring-border absolute left-1/2 top-1/2 block -translate-x-1/2 -translate-y-1/2 rounded-full border',
                !reducedMotion && 'hero-pulse-ring',
              ]
                .filter(Boolean)
                .join(' ')}
              style={{
                width: `${120 + i * 56}px`,
                height: `${72 + i * 32}px`,
                animationDelay: `${i * 1.1}s`,
              }}
            />
          ))}
        </div>

        <HudCorners />

        <CompGraph active={!reducedMotion} />

        <ScanLine active={!reducedMotion} />

        <div
          className={[
            'absolute inset-0 z-[1] flex items-center justify-center',
            !reducedMotion && 'hero-building-orbit',
          ]
            .filter(Boolean)
            .join(' ')}
          style={{ perspective: '900px' }}
        >
          <IsometricBuilding scanActive={!reducedMotion} />
        </div>

        <HeroCtaRipple rippleKey={ctaRippleKey} reducedMotion={reducedMotion} />

        <BoroughHint reducedMotion={reducedMotion} />

        <RotatingMetricTags reducedMotion={reducedMotion} />
      </div>
    </div>
  )
}
