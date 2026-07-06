import { useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion'
import { dealLabelBadgeClasses } from '../utils/dealLabelBadge'
import { modelConfidenceBadgeClasses } from '../utils/modelConfidence'

/**
 * Sample NYC properties the hero cycles through.
 * These are illustrative examples only — not real listings.
 */
const HERO_SAMPLES = [
  {
    address: '47 Hicks St · Brooklyn',
    price: 1_185_000,
    p10: 990_000,
    p90: 1_380_000,
    tier: 'high',
    tierLabel: 'High Confidence',
    deal: 'Buy',
  },
  {
    address: '2310 3rd Ave · E. Harlem',
    price: 875_000,
    p10: 740_000,
    p90: 1_020_000,
    tier: 'directional',
    tierLabel: 'Directional',
    deal: 'Hold',
  },
  {
    address: '91-14 Springfield · Queens',
    price: 620_000,
    p10: 530_000,
    p90: 730_000,
    tier: 'high',
    tierLabel: 'High Confidence',
    deal: 'Avoid',
  },
]

const PHASE = { AMBIENT: 0, INGEST: 1, COMPUTE: 2, RESOLVE: 3, VERDICT: 4 }

const COMP_NODES = [
  { x: 13, y: 28, linkClass: 'hero-comp-link-0', nodeClass: 'hero-comp-node-0', labelAnchor: 'start', labelDx: 3 },
  { x: 87, y: 22, linkClass: 'hero-comp-link-1', nodeClass: 'hero-comp-node-1', labelAnchor: 'end',   labelDx: -3 },
  { x: 9,  y: 50, linkClass: 'hero-comp-link-2', nodeClass: 'hero-comp-node-2', labelAnchor: 'start', labelDx: 3 },
  { x: 91, y: 54, linkClass: 'hero-comp-link-3', nodeClass: 'hero-comp-node-3', labelAnchor: 'end',   labelDx: -3 },
  { x: 18, y: 72, linkClass: 'hero-comp-link-4', nodeClass: 'hero-comp-node-4', labelAnchor: 'start', labelDx: 3 },
  { x: 82, y: 68, linkClass: 'hero-comp-link-5', nodeClass: 'hero-comp-node-5', labelAnchor: 'end',   labelDx: -3 },
]

const BUILDING_CENTER = { x: 50, y: 50 }
const BOROUGHS = ['Manhattan', 'Brooklyn']
const BOROUGH_CYCLE_MS = 4500

// ─── Sequence controller ──────────────────────────────────────────────────────

/**
 * Drives the 4-beat inference animation:
 *   INGEST → COMPUTE → RESOLVE (count-up) → VERDICT (confidence + deal)
 * then cycles through HERO_SAMPLES every ~5 s.
 */
function useHeroSequence(reducedMotion) {
  const [phase, setPhase] = useState(reducedMotion ? PHASE.VERDICT : PHASE.AMBIENT)
  const [sampleIndex, setSampleIndex] = useState(0)
  const [readoutKey, setReadoutKey] = useState(0)

  useEffect(() => {
    if (reducedMotion) return

    // Use a shared Set so the cleanup can clear every timer, including
    // those created by recursive cycleReadout calls.
    const pending = new Set()

    const after = (fn, ms) => {
      const t = setTimeout(() => {
        pending.delete(t)
        fn()
      }, ms)
      pending.add(t)
    }

    let nextSample = 0

    const cycleReadout = (delayMs) => {
      after(() => {
        nextSample = (nextSample + 1) % HERO_SAMPLES.length
        setSampleIndex(nextSample)
        setReadoutKey((k) => k + 1)
        setPhase(PHASE.RESOLVE)
        after(() => {
          setPhase(PHASE.VERDICT)
          cycleReadout(5000)
        }, 1200)
      }, delayMs)
    }

    // Intro sequence (runs once)
    after(() => setPhase(PHASE.INGEST), 500)
    after(() => setPhase(PHASE.COMPUTE), 1300)
    after(() => setPhase(PHASE.RESOLVE), 2200)
    after(() => {
      setPhase(PHASE.VERDICT)
      cycleReadout(5000)
    }, 3300)

    return () => pending.forEach(clearTimeout)
  }, [reducedMotion])

  return { phase, sampleIndex, readoutKey }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

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
    if (reducedMotion) return
    const id = setInterval(() => setIndex((i) => (i + 1) % BOROUGHS.length), BOROUGH_CYCLE_MS)
    return () => clearInterval(id)
  }, [reducedMotion])
  const borough = reducedMotion ? 'Manhattan · Brooklyn' : BOROUGHS[index]
  return (
    <p
      className="pointer-events-none absolute bottom-3 right-3 z-[3] font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500 dark:text-cyan-500/30"
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
    <div key={rippleKey} className="pointer-events-none absolute inset-0 z-[5]" aria-hidden>
      <span className="hero-cta-ripple-beam" />
      <span className="hero-cta-ripple-ring" />
    </div>
  )
}

function CompGraph({ active }) {
  return (
    <svg
      className="hero-comp-graph hero-parallax-shallow pointer-events-none absolute inset-0 z-[2] h-full w-full"
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
        {COMP_NODES.map((node, i) => (
          <g key={`comp-${i}`}>
            <circle
              cx={node.x}
              cy={node.y}
              r="1.4"
              className={[
                'hero-comp-node',
                active ? node.nodeClass : 'hero-comp-node-static',
              ].join(' ')}
            />
            {active && (
              <text
                x={node.x + node.labelDx}
                y={node.y - 2.8}
                textAnchor={node.labelAnchor}
                fontSize="2.4"
                fontFamily="monospace"
                letterSpacing="0.04em"
                className={['hero-comp-node', node.nodeClass].join(' ')}
                style={{ fontWeight: 600 }}
              >
                COMP {i + 1}
              </text>
            )}
          </g>
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
          'radial-gradient(ellipse 55% 62% at 50% 50%, black 15%, transparent 72%)',
        WebkitMaskImage:
          'radial-gradient(ellipse 55% 62% at 50% 50%, black 15%, transparent 72%)',
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

/**
 * NYC apartment block in isometric projection.
 *
 * Geometry (viewBox 240×280):
 *   Ground corners: Left=(48,218) Front=(120,258) Right=(192,218)
 *   Roof corners:   Left=(48,48)  Front=(120,88)  Right=(192,48)  Back=(120,8)
 *
 * Face parametrics (point on face at normalized position s∈[0,1], t∈[0,1]):
 *   Front face: P(s,t) = (120+72s, 88−40s+170t)
 *   Left  face: P(s,t) = (48+72s,  48+40s+170t)
 *
 * Window centers are spaced evenly and pre-computed from those parametrics.
 */
function IsometricBuilding({ scanActive }) {
  return (
    <svg
      viewBox="0 0 240 280"
      className="hero-building-svg h-full w-full max-h-[min(52vw,220px)] max-w-[min(52vw,192px)]"
      aria-hidden
    >
      <defs>
        <linearGradient id="hero-face-front" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" className="hero-building-face-front" />
          <stop offset="100%" className="hero-building-face-front" stopOpacity="0.05" />
        </linearGradient>
        <linearGradient id="hero-face-side" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" className="hero-building-face-side" />
          <stop offset="100%" className="hero-building-face-side" stopOpacity="0.03" />
        </linearGradient>
        <linearGradient id="hero-face-top" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" className="hero-building-face-top" />
          <stop offset="100%" className="hero-building-face-top" stopOpacity="0.14" />
        </linearGradient>
      </defs>

      {/* Ground shadow */}
      <ellipse cx="120" cy="254" rx="82" ry="16" className="hero-building-shadow" />

      {/* ── Main body faces ───────────────────────────── */}
      <g fill="none" strokeLinejoin="round">
        {/* Roof / top face */}
        <path
          d="M48,48 L120,8 L192,48 L120,88 Z"
          fill="url(#hero-face-top)"
          className="hero-building-stroke"
          strokeWidth="1.2"
        />
        {/* Left / side face */}
        <path
          d="M48,218 L48,48 L120,88 L120,258 Z"
          fill="url(#hero-face-side)"
          className="hero-building-stroke"
          strokeWidth="1.2"
        />
        {/* Right / front face */}
        <path
          d="M120,258 L120,88 L192,48 L192,218 Z"
          fill="url(#hero-face-front)"
          className="hero-building-stroke"
          strokeWidth="1.2"
        />
      </g>

      {/* ── Glowing corner & roofline edges ──────────── */}
      <g fill="none" strokeLinejoin="round" className="hero-building-edge">
        {/* Vertical front edge (most visible) */}
        <line x1="120" y1="88" x2="120" y2="258" strokeWidth="2.2" />
        {/* Vertical left edge */}
        <line x1="48" y1="48" x2="48" y2="218" strokeWidth="1.6" opacity="0.7" />
        {/* Vertical right edge */}
        <line x1="192" y1="48" x2="192" y2="218" strokeWidth="1.6" />
        {/* Roofline outline */}
        <path d="M48,48 L120,8 L192,48 L120,88 Z" strokeWidth="1.4" />
      </g>

      {/* ── Floor-plate dividers (5 stories = 4 lines) ── */}
      <g className="hero-building-stroke" fill="none" strokeWidth="0.5" opacity="0.35">
        <line x1="48" y1="82"  x2="120" y2="122" /><line x1="120" y1="122" x2="192" y2="82" />
        <line x1="48" y1="116" x2="120" y2="156" /><line x1="120" y1="156" x2="192" y2="116" />
        <line x1="48" y1="150" x2="120" y2="190" /><line x1="120" y1="190" x2="192" y2="150" />
        <line x1="48" y1="184" x2="120" y2="224" /><line x1="120" y1="224" x2="192" y2="184" />
      </g>

      {/* ── Windows: front (right) face — 3 cols × 5 rows ── */}
      <g
        className={['hero-building-windows', scanActive ? 'hero-window-glow' : undefined]
          .filter(Boolean).join(' ')}
        fill="none"
        strokeWidth="0.85"
      >
        {/* Row 1 */}
        <path d="M125,87 L139,79 L139,110 L125,118 Z" />
        <path d="M149,74 L163,66 L163,96  L149,104 Z" />
        <path d="M173,60 L187,52 L187,83  L173,91  Z" />
        {/* Row 2 */}
        <path d="M125,121 L139,113 L139,144 L125,152 Z" />
        <path d="M149,108 L163,100 L163,130 L149,138 Z" />
        <path d="M173,94  L187,86  L187,117 L173,125 Z" />
        {/* Row 3 */}
        <path d="M125,155 L139,147 L139,178 L125,186 Z" />
        <path d="M149,142 L163,134 L163,164 L149,172 Z" />
        <path d="M173,128 L187,120 L187,151 L173,159 Z" />
        {/* Row 4 */}
        <path d="M125,189 L139,181 L139,212 L125,220 Z" />
        <path d="M149,176 L163,168 L163,198 L149,206 Z" />
        <path d="M173,162 L187,154 L187,185 L173,193 Z" />
        {/* Row 5 */}
        <path d="M125,223 L139,215 L139,246 L125,254 Z" />
        <path d="M149,210 L163,202 L163,232 L149,240 Z" />
        <path d="M173,196 L187,188 L187,219 L173,227 Z" />
      </g>

      {/* ── Windows: left (side) face — 2 cols × 5 rows ── */}
      <g
        className={['hero-building-windows', scanActive ? 'hero-window-glow hero-window-glow-delay' : undefined]
          .filter(Boolean).join(' ')}
        fill="none"
        strokeWidth="0.85"
      >
        {/* Row 1 */}
        <path d="M57,55  L75,65  L75,95  L57,85  Z" />
        <path d="M93,75  L111,85 L111,115 L93,105 Z" />
        {/* Row 2 */}
        <path d="M57,89  L75,99  L75,129 L57,119 Z" />
        <path d="M93,109 L111,119 L111,149 L93,139 Z" />
        {/* Row 3 */}
        <path d="M57,123 L75,133 L75,163 L57,153 Z" />
        <path d="M93,143 L111,153 L111,183 L93,173 Z" />
        {/* Row 4 */}
        <path d="M57,157 L75,167 L75,197 L57,187 Z" />
        <path d="M93,177 L111,187 L111,217 L93,207 Z" />
        {/* Row 5 */}
        <path d="M57,191 L75,201 L75,231 L57,221 Z" />
        <path d="M93,211 L111,221 L111,251 L93,241 Z" />
      </g>

      {/* ── Entrance door (front face center base) ──── */}
      <path
        d="M150,216 L163,209 L163,234 L150,242 Z"
        className={['hero-building-windows', scanActive ? 'hero-window-glow hero-window-glow-delay-2' : undefined]
          .filter(Boolean).join(' ')}
        fill="none"
        strokeWidth="1"
      />

      {/* ── Animated signal / data lines ─────────────── */}
      <g className="hero-building-signal" strokeWidth="1.1" fill="none">
        <path d="M22,58 Q 50,76 78,100"  className="hero-signal-line"              strokeDasharray="4 6" />
        <path d="M218,54 Q 188,72 158,96" className="hero-signal-line hero-signal-line-delay"  strokeDasharray="4 6" />
        <path d="M204,204 Q 172,188 148,172" className="hero-signal-line hero-signal-line-delay-2" strokeDasharray="4 6" />
      </g>
    </svg>
  )
}

/**
 * 28 pre-positioned particles covering all four quadrants (viewBox 0–100).
 * Negative begin values start each animation mid-cycle so the panel is
 * already populated the moment it mounts — no empty-then-fill flash.
 */
const AMBIENT_PARTICLES = [
  // left column
  { cx:  7, cy:  9, r: 0.55, o: 0.32, dur: 6.2, delay: 0.0, drift: 8 },
  { cx:  3, cy: 28, r: 0.50, o: 0.30, dur: 7.1, delay: 3.0, drift: 8 },
  { cx: 15, cy: 44, r: 0.45, o: 0.28, dur: 6.5, delay: 2.1, drift: 7 },
  { cx:  8, cy: 62, r: 0.55, o: 0.34, dur: 5.9, delay: 4.2, drift: 9 },
  { cx: 18, cy: 78, r: 0.42, o: 0.26, dur: 6.8, delay: 1.7, drift: 8 },
  { cx:  5, cy: 90, r: 0.50, o: 0.30, dur: 7.4, delay: 0.5, drift: 9 },
  // right column
  { cx: 94, cy: 17, r: 0.52, o: 0.32, dur: 5.5, delay: 0.8, drift: 7 },
  { cx: 88, cy: 32, r: 0.42, o: 0.26, dur: 7.3, delay: 3.4, drift: 8 },
  { cx: 96, cy: 48, r: 0.50, o: 0.30, dur: 6.1, delay: 1.2, drift: 7 },
  { cx: 82, cy: 61, r: 0.55, o: 0.34, dur: 6.7, delay: 4.0, drift: 8 },
  { cx: 93, cy: 76, r: 0.42, o: 0.26, dur: 5.8, delay: 2.3, drift: 8 },
  { cx: 86, cy: 88, r: 0.50, o: 0.30, dur: 7.2, delay: 0.3, drift: 9 },
  // mid-left (beside building)
  { cx: 20, cy: 14, r: 0.42, o: 0.26, dur: 5.7, delay: 1.4, drift: 7 },
  { cx: 26, cy: 35, r: 0.52, o: 0.32, dur: 5.6, delay: 1.0, drift: 7 },
  { cx: 34, cy: 68, r: 0.42, o: 0.26, dur: 7.0, delay: 2.8, drift: 8 },
  { cx: 28, cy: 85, r: 0.55, o: 0.34, dur: 6.3, delay: 4.6, drift: 9 },
  // mid-right (beside building)
  { cx: 72, cy: 12, r: 0.50, o: 0.30, dur: 5.4, delay: 0.6, drift: 7 },
  { cx: 68, cy: 38, r: 0.42, o: 0.26, dur: 6.9, delay: 3.2, drift: 8 },
  { cx: 76, cy: 64, r: 0.52, o: 0.32, dur: 5.7, delay: 1.9, drift: 8 },
  { cx: 70, cy: 84, r: 0.45, o: 0.28, dur: 7.5, delay: 0.2, drift: 9 },
  // top center
  { cx: 40, cy:  5, r: 0.42, o: 0.26, dur: 6.1, delay: 2.5, drift: 6 },
  { cx: 52, cy:  3, r: 0.50, o: 0.30, dur: 5.9, delay: 1.1, drift: 7 },
  { cx: 62, cy:  8, r: 0.45, o: 0.28, dur: 6.6, delay: 3.8, drift: 6 },
  // bottom center
  { cx: 44, cy: 92, r: 0.55, o: 0.34, dur: 7.1, delay: 0.4, drift: 9 },
  { cx: 56, cy: 95, r: 0.42, o: 0.26, dur: 6.0, delay: 2.0, drift: 8 },
  { cx: 64, cy: 90, r: 0.50, o: 0.30, dur: 5.5, delay: 3.5, drift: 9 },
  // extra scatter
  { cx: 84, cy:  7, r: 0.45, o: 0.28, dur: 6.0, delay: 2.6, drift: 7 },
  { cx: 30, cy: 10, r: 0.45, o: 0.28, dur: 6.4, delay: 3.7, drift: 7 },
]

/**
 * Renders ambient particles as pure SVG — no canvas, no requestAnimationFrame,
 * no sizing dependencies. Works immediately on mount.
 */
function ParticleField({ active }) {
  if (!active) return null

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 z-[1] h-full w-full"
      aria-hidden
    >
      {AMBIENT_PARTICLES.map((p, i) => (
        <circle key={i} cx={p.cx} cy={p.cy} r={p.r} fill="rgb(34,211,238)">
          <animate
            attributeName="cy"
            from={p.cy}
            to={p.cy - p.drift}
            dur={`${p.dur}s`}
            begin={`-${p.delay}s`}
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values={`0;${p.o};${p.o};0`}
            keyTimes="0;0.2;0.8;1"
            dur={`${p.dur}s`}
            begin={`-${p.delay}s`}
            repeatCount="indefinite"
          />
        </circle>
      ))}
    </svg>
  )
}

/**
 * Full-width result card pinned to the bottom of the panel.
 * Shows: address + deal badge, big count-up price, P10–P90 range bar.
 * Uses a dark backdrop so it reads clearly against the building.
 */
function ValuationReadout({ sample, readoutKey, visible, reducedMotion, verdictVisible }) {
  const [price, setPrice] = useState(reducedMotion ? sample.price : 0)
  const [rangeActive, setRangeActive] = useState(reducedMotion)

  const markerPct = Math.max(
    4,
    Math.min(96, ((sample.price - sample.p10) / (sample.p90 - sample.p10)) * 100)
  )

  useEffect(() => {
    if (reducedMotion) {
      setPrice(sample.price)
      setRangeActive(true)
      return
    }

    setPrice(0)
    setRangeActive(false)

    if (!visible) return

    const DURATION = 1000
    const t0 = performance.now()
    let rafId

    const tick = (now) => {
      const t = Math.min(1, (now - t0) / DURATION)
      const eased = 1 - (1 - t) ** 3
      setPrice(Math.round(sample.price * eased))
      if (t < 1) rafId = requestAnimationFrame(tick)
    }

    rafId = requestAnimationFrame(tick)
    const rangeTimer = setTimeout(() => setRangeActive(true), 350)

    return () => {
      cancelAnimationFrame(rafId)
      clearTimeout(rangeTimer)
    }
  // readoutKey is the cycling trigger — including it restarts the effect on each cycle
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readoutKey, visible, reducedMotion])

  if (!visible && !reducedMotion) return null

  return (
    <div
      key={readoutKey}
      className="hero-readout-in pointer-events-none absolute left-[5%] right-[5%] z-[4]"
      style={{ bottom: '4%' }}
      aria-hidden
    >
      <div className="rounded-xl border border-cyan-500/20 bg-slate-950/90 px-4 pb-4 pt-3 shadow-[0_0_30px_rgba(34,211,238,0.07)] backdrop-blur-md dark:border-cyan-400/15">
        {/* Address + deal badge row */}
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="truncate font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-500/55 dark:text-cyan-400/40">
            {sample.address}
          </p>
          {(verdictVisible || reducedMotion) && (
            <span
              key={`deal-${readoutKey}`}
              className={[
                'hero-verdict-in shrink-0 rounded-full border px-2.5 py-0.5',
                'font-mono text-[10px] font-bold uppercase tracking-wide',
                dealLabelBadgeClasses(sample.deal),
              ].join(' ')}
            >
              {sample.deal}
            </span>
          )}
        </div>

        {/* Big animated price */}
        <p
          className="font-mono text-[clamp(1.6rem,4.5vw,2.1rem)] font-bold leading-none tabular-nums text-cyan-500 dark:text-cyan-300"
          style={{ textShadow: '0 0 28px rgba(34,211,238,0.65), 0 0 56px rgba(34,211,238,0.22)' }}
        >
          ${price.toLocaleString()}
        </p>

        {/* P10–P90 range bar */}
        <div className="mt-3">
          <div className="mb-1.5 flex items-center justify-between font-mono text-[9px] text-cyan-500/40 dark:text-cyan-400/30">
            <span>P10 · ${(sample.p10 / 1000).toFixed(0)}k</span>
            <span className="opacity-70">predicted value</span>
            <span>${(sample.p90 / 1000).toFixed(0)}k · P90</span>
          </div>
          <div className="relative h-1.5 overflow-visible rounded-full bg-cyan-500/10 dark:bg-cyan-900/30">
            <div
              className="hero-range-fill absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-cyan-700 via-cyan-500 to-cyan-400 dark:from-cyan-600 dark:to-cyan-300"
              style={{ width: rangeActive ? `${markerPct}%` : '0%' }}
            />
            <div
              className="hero-range-marker absolute top-1/2 h-3.5 w-3.5 rounded-full border-2 border-cyan-300 bg-white dark:border-cyan-200 dark:bg-slate-900"
              style={{
                left: rangeActive ? `${markerPct}%` : '0%',
                boxShadow: '0 0 10px 2px rgba(34,211,238,0.9)',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

/** Confidence tier pill — snaps in at top-right during the VERDICT phase. */
function ConfidencePill({ sample, visible, reducedMotion }) {
  if (!visible && !reducedMotion) return null
  return (
    <div
      key={`cp-${sample.address}`}
      className={[
        'hero-verdict-in pointer-events-none absolute right-3 top-3 z-[4]',
        'rounded-full border px-3 py-1',
        'font-mono text-[10px] font-semibold uppercase tracking-wide',
        modelConfidenceBadgeClasses(sample.tier),
      ].join(' ')}
      aria-hidden
    >
      {sample.tierLabel}
    </div>
  )
}

// ─── Main export ──────────────────────────────────────────────────────────────

export default function HeroVisual({ ctaRippleKey = 0 }) {
  const reducedMotion = usePrefersReducedMotion()
  const { phase, sampleIndex, readoutKey } = useHeroSequence(reducedMotion)
  const sample = HERO_SAMPLES[sampleIndex]
  const panelRef = useRef(null)

  // Cursor parallax — writes --hero-mx / --hero-my CSS vars without triggering
  // React re-renders. The CSS classes hero-parallax-deep / hero-parallax-shallow
  // consume these vars to create a depth illusion.
  useEffect(() => {
    if (reducedMotion) return
    const panel = panelRef.current
    if (!panel) return

    let ticking = false

    const onMove = (e) => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(() => {
        const rect = panel.getBoundingClientRect()
        const mx = ((e.clientX - rect.left) / rect.width - 0.5) * 2
        const my = ((e.clientY - rect.top) / rect.height - 0.5) * 2
        panel.style.setProperty('--hero-mx', mx.toFixed(3))
        panel.style.setProperty('--hero-my', my.toFixed(3))
        ticking = false
      })
    }

    const onLeave = () => {
      panel.style.setProperty('--hero-mx', '0')
      panel.style.setProperty('--hero-my', '0')
    }

    panel.addEventListener('pointermove', onMove)
    panel.addEventListener('pointerleave', onLeave)
    return () => {
      panel.removeEventListener('pointermove', onMove)
      panel.removeEventListener('pointerleave', onLeave)
    }
  }, [reducedMotion])

  const compActive = phase >= PHASE.INGEST && !reducedMotion
  const readoutVisible = phase >= PHASE.RESOLVE || reducedMotion
  const verdictVisible = phase >= PHASE.VERDICT || reducedMotion

  return (
    <div
      className="relative mx-auto w-full max-w-lg lg:mx-0 lg:max-w-none"
      aria-hidden
    >
      <div
        ref={panelRef}
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

        <div className="hero-visual-grid pointer-events-none absolute inset-0 bg-[length:28px_28px] mask-[radial-gradient(ellipse_80%_70%_at_50%_50%,black_20%,transparent_75%)]" />

        <ParticleField active={!reducedMotion} />

        <div className="pointer-events-none absolute left-1/2 top-[50%] -translate-x-1/2 -translate-y-1/2">
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

        <CompGraph active={compActive} />

        <ScanLine active={!reducedMotion} />

        {/* Parallax wrapper keeps orbit animation separate from the 2-D translate */}
        <div className="hero-parallax-deep pointer-events-none absolute inset-0 z-[1] flex items-center justify-center">
          <div
            className={[
              'flex h-full w-full items-center justify-center',
              !reducedMotion && 'hero-building-orbit',
            ]
              .filter(Boolean)
              .join(' ')}
            style={{ perspective: '900px' }}
          >
            <IsometricBuilding scanActive={!reducedMotion} />
          </div>
        </div>

        <ValuationReadout
          sample={sample}
          readoutKey={readoutKey}
          visible={readoutVisible}
          verdictVisible={verdictVisible}
          reducedMotion={reducedMotion}
        />

        <ConfidencePill sample={sample} visible={verdictVisible} reducedMotion={reducedMotion} />

        <HeroCtaRipple rippleKey={ctaRippleKey} reducedMotion={reducedMotion} />

        <BoroughHint reducedMotion={reducedMotion} />
      </div>
    </div>
  )
}
