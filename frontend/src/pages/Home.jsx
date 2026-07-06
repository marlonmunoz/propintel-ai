import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BarChart3, Brain, ChevronLeft, ChevronRight, ShieldCheck } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import HeroVisual from '../components/HeroVisual'
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion'

const features = [
  {
    icon: BarChart3,
    title: 'ML-Powered Valuation',
    description:
      'Segment-routed XGBoost and LightGBM models trained on 323k NYC sales (2019–2026). Building class selects the best-fit model — single-family, multi-family (2–3 unit), condo, co-op, or pooled rentals.',
  },
  {
    icon: Brain,
    title: 'AI Investment Analysis',
    description:
      'Get a full investment breakdown: ROI estimate, valuation gap, deal label (Buy / Hold / Avoid), and an LLM-generated narrative explanation.',
  },
  {
    icon: ShieldCheck,
    title: 'Production-Grade API',
    description:
      'Built on a hardened FastAPI backend with authentication, rate limiting, structured logging, and a consistent JSON contract.',
  },
]

/** Snapshot from `ml/artifacts/metadata/*.json` — update targets when you retrain. */
const modelMetrics = [
  {
    label: 'Condo valuations',
    segment: 'Real-property unit lots',
    target: 0.83,
    decimals: 2,
    suffix: 'R²',
    detail: 'Split condo model with DOF unit sqft + ownership share — 13.9% median error on holdout',
  },
  {
    label: 'Single-family homes',
    segment: 'Owner-occupier baseline',
    target: 0.72,
    decimals: 2,
    suffix: 'R²',
    detail: 'Strongest traditional segment — 14.5% median error, time-based holdout',
  },
  {
    label: 'Segment models',
    segment: 'Production routing',
    target: 6,
    decimals: 0,
    suffix: 'models',
    detail: 'Global fallback + condo, co-op, multi-family, rentals, and single-family',
  },
]

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3
}

/** Fires once when the element intersects the viewport (good for scroll-triggered animations). */
function useInViewOnce(options = {}) {
  const { threshold = 0.2, rootMargin = '0px 0px -8% 0px' } = options
  const ref = useRef(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || inView) return undefined
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setInView(true)
      },
      { threshold, rootMargin }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [inView, threshold, rootMargin])

  return [ref, inView]
}

function CountUpMetric({ target, decimals, suffix, start, staggerMs = 0 }) {
  const reducedMotion = usePrefersReducedMotion()
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (!start || reducedMotion) return undefined

    let rafId = 0
    const delayTimer = window.setTimeout(() => {
      const durationMs = 1850
      const t0 = performance.now()

      const tick = (now) => {
        const elapsed = now - t0
        const t = Math.min(1, elapsed / durationMs)
        const eased = easeOutCubic(t)
        setDisplay(target * eased)
        if (t < 1) {
          rafId = requestAnimationFrame(tick)
        }
      }
      rafId = requestAnimationFrame(tick)
    }, staggerMs)

    return () => {
      clearTimeout(delayTimer)
      cancelAnimationFrame(rafId)
    }
  }, [start, target, reducedMotion, staggerMs])

  const raw = !start ? 0 : reducedMotion ? target : display
  const text = decimals > 0 ? raw.toFixed(decimals) : String(Math.round(raw))

  return (
    <p className="mt-3 font-mono text-3xl font-bold tabular-nums text-cyan-600 dark:text-cyan-400">
      {text}
      <span className="ml-1 text-lg font-semibold text-slate-500 dark:text-slate-400">{suffix}</span>
    </p>
  )
}

function FeatureCard({ icon, title, description, className = '' }) {
  const Icon = icon
  return (
    <div
      className={`flex h-full flex-col rounded-2xl border border-slate-200 bg-slate-50 p-6 transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-slate-600 ${className}`}
    >
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10">
        <Icon className="h-5 w-5 text-cyan-500 dark:text-cyan-400" />
      </div>
      <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  )
}

function MobileFeatureCarousel({ items }) {
  const [index, setIndex] = useState(0)
  const reducedMotion = usePrefersReducedMotion()

  useEffect(() => {
    if (reducedMotion || items.length <= 1) return undefined
    const t = window.setInterval(() => {
      setIndex((i) => (i + 1) % items.length)
    }, 6500)
    return () => window.clearInterval(t)
  }, [items.length, reducedMotion])

  const go = (delta) => {
    setIndex((i) => (i + delta + items.length) % items.length)
  }

  const n = items.length
  /* Track is n× viewport width; each slide is 1/n of the track so translateX(-index/n * 100%) moves exactly one card (CSS % on translate is relative to the track, not each slide). */
  const trackStyle =
    n <= 0
      ? undefined
      : {
          width: `${n * 100}%`,
          transform: `translateX(-${(index * 100) / n}%)`,
        }

  return (
    <div className="md:hidden">
      <div className="relative min-w-0 overflow-hidden rounded-2xl">
        <div
          className={`flex ${reducedMotion ? '' : 'transition-transform duration-500 ease-out'}`}
          style={trackStyle}
        >
          {items.map(({ icon, title, description }) => (
            <div
              key={title}
              className="shrink-0"
              style={{ width: n > 0 ? `${100 / n}%` : undefined }}
            >
              <FeatureCard icon={icon} title={title} description={description} />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-center gap-3">
        <button
          type="button"
          onClick={() => go(-1)}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-slate-200 text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label="Previous feature"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div className="flex gap-1" role="tablist" aria-label="Feature slides">
          {items.map(({ title }, i) => (
            <button
              key={title}
              type="button"
              role="tab"
              aria-selected={i === index}
              aria-label={`Show feature: ${title}`}
              onClick={() => setIndex(i)}
              className="flex h-8 w-6 items-center justify-center"
            >
              <span
                className={`h-2 rounded-full transition-all ${
                  i === index ? 'w-8 bg-cyan-500' : 'w-2 bg-slate-300 dark:bg-slate-600'
                }`}
              />
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => go(1)}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-slate-200 text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label="Next feature"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}

const HERO_RIPPLE_NAV_MS = 720

export default function Home() {
  const navigate = useNavigate()
  const reducedMotion = usePrefersReducedMotion()
  const [metricsRef, metricsInView] = useInViewOnce()
  const [heroCtaRippleKey, setHeroCtaRippleKey] = useState(0)
  const rippleNavTimeoutRef = useRef(null)

  useEffect(
    () => () => {
      if (rippleNavTimeoutRef.current) window.clearTimeout(rippleNavTimeoutRef.current)
    },
    []
  )

  const onAnalyzeCtaClick = useCallback(
    (e) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return

      const isLg = window.matchMedia('(min-width: 1024px)').matches
      if (!isLg || reducedMotion) return

      e.preventDefault()
      setHeroCtaRippleKey((k) => k + 1)
      if (rippleNavTimeoutRef.current) window.clearTimeout(rippleNavTimeoutRef.current)
      rippleNavTimeoutRef.current = window.setTimeout(() => {
        navigate('/analyze')
      }, HERO_RIPPLE_NAV_MS)
    },
    [navigate, reducedMotion]
  )

  return (
    <div className="flex min-h-screen min-w-0 flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <div className="flex min-w-0 flex-1 flex-col">
      {/* Hero — copy + 2.5D visual on lg; stacked on mobile */}
      <section className="mx-auto max-w-6xl px-4 pb-12 pt-12 sm:px-6 sm:pb-14 sm:pt-16 lg:pt-20">
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-12">
          <div className="text-center lg:text-left">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.22em] text-cyan-600 dark:text-cyan-400">
          PropIntel AI
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
          Buy, hold, or sell—with NYC sales data behind your instinct
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-sm leading-relaxed text-slate-500 sm:text-base lg:mx-0 dark:text-slate-400">
          Valuations, deal signals, and plain language—whether you are buying a home or sizing an
          investment—grounded in NYC residential sales. Decision support, not a crystal ball. Not
          financial, legal, or investment advice.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 lg:justify-start">
          <Link
            to="/analyze"
            onClick={onAnalyzeCtaClick}
            className="rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            Analyze Property
          </Link>
        </div>
          </div>
          <HeroVisual ctaRippleKey={heroCtaRippleKey} />
        </div>
      </section>

      {/* Model metrics — static numbers from training metadata */}
      <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">
          Model performance
        </p>
        <h2 className="mx-auto mt-2 max-w-2xl text-center text-lg font-semibold text-slate-900 dark:text-white">
          Built on real NYC sales — segment models, not a single generic fit
        </h2>
        <div ref={metricsRef} className="mt-8 grid gap-4 sm:grid-cols-3">
          {modelMetrics.map((m, index) => (
            <div
              key={m.label}
              className="rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-5 text-center dark:border-slate-800 dark:from-slate-900/80 dark:to-slate-950"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {m.label}
              </p>
              <p className="mt-1 text-sm font-medium text-slate-700 dark:text-slate-300">{m.segment}</p>
              <CountUpMetric
                target={m.target}
                decimals={m.decimals}
                suffix={m.suffix}
                start={metricsInView}
                staggerMs={index * 180}
              />
              <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">{m.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features — carousel on small screens, grid from md up */}
      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">
          Product
        </p>
        <h2 className="mt-2 text-center text-2xl font-bold text-slate-900 dark:text-white">
          What You Get
        </h2>
        <p className="mx-auto mt-2 mb-6 max-w-xl text-center text-sm text-slate-500 md:mb-0 dark:text-slate-400">
          On phones, swipe or use the arrows — features rotate automatically unless you prefer reduced motion.
        </p>

        <MobileFeatureCarousel items={features} />

        <div className="mt-8 hidden gap-6 md:grid md:grid-cols-3">
          {features.map(({ icon, title, description }) => (
            <FeatureCard key={title} icon={icon} title={title} description={description} />
          ))}
        </div>
      </section>
      </div>

      <Footer />
    </div>
  )
}
