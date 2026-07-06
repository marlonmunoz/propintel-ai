import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check, Minus, Crown, Zap, HelpCircle, ChevronDown } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { useAuth } from '../context/AuthContext'
import { createCheckoutSession, createPortalSession } from '../services/billingApi'

// ── Feature comparison table data ────────────────────────────────────────────

const FEATURES = [
  {
    category: 'Valuation Engine',
    rows: [
      { label: 'AI-powered property valuations',      free: true,          pro: true },
      {
        label: 'Five segment-specific ML models',
        free: true,
        pro: true,
        hint: 'One-family · Multi-family · Condo/Co-op · Walkup rental · Elevator rental',
      },
      { label: 'P10/P90 confidence intervals',         free: true,          pro: true },
      { label: 'Deal scoring (Buy / Hold / Avoid)',    free: true,          pro: true },
      { label: 'AI investment narrative',              free: true,          pro: true },
    ],
  },
  {
    category: 'Usage & Portfolio',
    rows: [
      { label: 'Daily AI analyses',                   free: '10 / day',    pro: '200 / day' },
      { label: 'Saved properties',                    free: true,          pro: true },
      { label: 'Portfolio comparisons',               free: '2 at a time', pro: '10 at a time' },
      { label: 'CSV / PDF / print export',            free: true,          pro: true },
    ],
  },
  {
    category: 'Support',
    rows: [
      { label: 'Email support',                       free: true,          pro: true },
      { label: 'Priority support',                    free: false,         pro: true },
    ],
  },
]

// ── FAQ data ──────────────────────────────────────────────────────────────────

const FAQ = [
  {
    q: 'What counts as one AI analysis?',
    a: 'Each time you submit a property address and receive a full valuation — ML estimate, confidence range, deal score, and written investment narrative — that counts as one analysis. Viewing previously run results does not consume quota.',
  },
  {
    q: 'What happens when I hit the daily limit?',
    a: 'You can still view your saved portfolio and all previously run analyses. New analysis submissions are paused until your quota resets at midnight UTC. Upgrading to Pro immediately raises your limit to 200 per day.',
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Cancel from the Stripe billing portal at any time. Your Pro access continues until the end of the current billing period, then your account returns to Free with no further charges.',
  },
  {
    q: 'Is there a free trial of Pro?',
    a: 'The Free tier is effectively a permanent free plan — full access to the ML models and AI narratives, just capped at 10 analyses per day. No credit card required to sign up.',
  },
  {
    q: 'Which NYC boroughs and property types are covered?',
    a: 'All five boroughs: Manhattan, Brooklyn, Queens, The Bronx, and Staten Island. Five segments: one-family homes, multi-family (2–4 units), condos and co-ops, walkup rentals, and elevator rentals. Each segment has its own dedicated model trained on NYC public data.',
  },
  {
    q: 'How is PropIntel AI different from Zillow or StreetEasy?',
    a: 'PropIntel AI is built for investors and operators, not browsing buyers. Our models use NYC-specific data sources (PLUTO, ACRIS, DOF assessments) and each property type has its own dedicated ML model. You get a deal score, P10/P90 confidence range, and a written investment rationale — not just an estimated sale price.',
  },
]

// ── Sub-components ────────────────────────────────────────────────────────────

function FeatureValue({ value }) {
  if (value === true)
    return <Check className="mx-auto h-5 w-5 text-cyan-500" aria-label="Included" />
  if (value === false)
    return <Minus className="mx-auto h-4 w-4 text-slate-300 dark:text-slate-700" aria-label="Not included" />
  return (
    <span className="block text-center text-sm font-medium text-slate-700 dark:text-slate-300">
      {value}
    </span>
  )
}

function FaqItem({ q, a }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-slate-100 last:border-0 dark:border-slate-800">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start justify-between gap-4 py-5 text-left"
        aria-expanded={open}
      >
        <span className="text-sm font-semibold text-slate-900 dark:text-white">{q}</span>
        <ChevronDown
          className={`mt-0.5 h-4 w-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <p className="pb-5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{a}</p>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Pricing() {
  const { user, profile } = useAuth()
  const navigate = useNavigate()
  const [upgradeLoading, setUpgradeLoading] = useState(false)
  const [portalLoading, setPortalLoading] = useState(false)
  const [err, setErr] = useState(null)

  const role = profile?.role ?? 'user'
  const isPaid = role === 'paid' || role === 'admin'
  const isFreeUser = !!user && !isPaid

  async function handleUpgrade() {
    if (!user) {
      navigate('/register')
      return
    }
    setErr(null)
    setUpgradeLoading(true)
    try {
      const { url } = await createCheckoutSession()
      window.location.href = url
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not start checkout.')
      setUpgradeLoading(false)
    }
  }

  async function handlePortal() {
    setErr(null)
    setPortalLoading(true)
    try {
      const { url } = await createPortalSession()
      window.location.href = url
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not open billing portal.')
      setPortalLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      <Navbar />

      <main className="flex-1">
        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="px-4 pb-14 pt-16 text-center sm:px-6 sm:pt-20">
          <div className="mx-auto max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700 dark:border-cyan-800/50 dark:bg-cyan-950/40 dark:text-cyan-300">
              Simple pricing
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-5xl">
              Start free. Upgrade when ready.
            </h1>
            <p className="mt-4 text-lg leading-relaxed text-slate-600 dark:text-slate-400">
              Full ML valuation and AI investment analysis on every plan.
              No credit card required to get started.
            </p>
          </div>
        </section>

        {/* ── Tier cards ───────────────────────────────────────────────── */}
        <section className="px-4 pb-16 sm:px-6">
          <div className="mx-auto grid max-w-4xl gap-6 sm:grid-cols-2">

            {/* Free card */}
            <div className="flex flex-col rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-slate-400" />
                <span className="text-sm font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  Free
                </span>
              </div>

              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-slate-900 dark:text-white">$0</span>
                <span className="text-sm text-slate-400">/month</span>
              </div>

              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Everything you need to evaluate your first NYC deal.
              </p>

              <ul className="mt-6 space-y-3 text-sm text-slate-700 dark:text-slate-300">
                {[
                  '10 AI-powered analyses per day',
                  'All five property segment models',
                  'P10/P90 confidence intervals',
                  'Deal scoring (Buy / Hold / Avoid)',
                  'AI investment narrative',
                  'Portfolio saving &amp; CSV/PDF export',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-cyan-500" />
                    <span dangerouslySetInnerHTML={{ __html: item }} />
                  </li>
                ))}
              </ul>

              <div className="mt-auto pt-8">
                {!user ? (
                  <Link
                    to="/register"
                    className="block w-full rounded-xl border border-slate-200 bg-slate-50 py-3 text-center text-sm font-semibold text-slate-800 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700"
                  >
                    Get started free
                  </Link>
                ) : isPaid ? (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 py-3 text-center text-sm text-slate-400 dark:border-slate-700 dark:bg-slate-800">
                    Your previous plan
                  </div>
                ) : (
                  <div className="rounded-xl border border-cyan-200 bg-cyan-50 py-3 text-center text-sm font-semibold text-cyan-700 dark:border-cyan-800/50 dark:bg-cyan-950/30 dark:text-cyan-300">
                    ✓ Current plan
                  </div>
                )}
              </div>
            </div>

            {/* Pro card */}
            <div className="relative flex flex-col rounded-2xl border-2 border-cyan-500 bg-white p-8 shadow-xl shadow-cyan-500/10 dark:bg-slate-900">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                <span className="rounded-full bg-cyan-500 px-3.5 py-1 text-[11px] font-bold uppercase tracking-widest text-slate-950">
                  Most popular
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Crown className="h-5 w-5 text-cyan-500" />
                <span className="text-sm font-semibold uppercase tracking-widest text-cyan-600 dark:text-cyan-400">
                  Pro
                </span>
              </div>

              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-slate-900 dark:text-white">$29</span>
                <span className="text-sm text-slate-400">/month</span>
              </div>

              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                For active investors and operators running analyses daily.
              </p>

              <ul className="mt-6 space-y-3 text-sm text-slate-700 dark:text-slate-300">
                {[
                  '200 AI-powered analyses per day',
                  'Everything in Free',
                  'Compare up to 10 portfolio properties',
                  'Priority email support',
                  'Cancel anytime from billing portal',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-cyan-500" />
                    {item}
                  </li>
                ))}
              </ul>

              {err && (
                <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
                  {err}
                </p>
              )}

              <div className="mt-auto pt-8">
                {isPaid ? (
                  <button
                    type="button"
                    disabled={portalLoading}
                    onClick={() => void handlePortal()}
                    className="w-full rounded-xl bg-slate-100 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-200 disabled:opacity-60 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700"
                  >
                    {portalLoading ? 'Opening…' : 'Manage subscription'}
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      disabled={upgradeLoading}
                      onClick={() => void handleUpgrade()}
                      className="w-full rounded-xl bg-cyan-500 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
                    >
                      {upgradeLoading
                        ? 'Redirecting…'
                        : isFreeUser
                          ? 'Upgrade to Pro'
                          : 'Start with Pro'}
                    </button>
                    {isPaid && (
                      <div className="mt-2 rounded-lg border border-cyan-200 bg-cyan-50 py-1.5 text-center text-xs font-semibold text-cyan-700 dark:border-cyan-800/40 dark:bg-cyan-950/20 dark:text-cyan-300">
                        ✓ Current plan
                      </div>
                    )}
                  </>
                )}
                <p className="mt-2 text-center text-xs text-slate-400">
                  Secure checkout powered by Stripe
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── Full feature comparison table ────────────────────────────── */}
        <section className="px-4 pb-20 sm:px-6">
          <div className="mx-auto max-w-4xl">
            <h2 className="mb-8 text-center text-xl font-bold text-slate-900 dark:text-white">
              Full comparison
            </h2>

            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_96px_96px] border-b border-slate-200 bg-slate-50 px-6 py-3.5 dark:border-slate-800 dark:bg-slate-900/80">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Feature
                </span>
                <span className="text-center text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Free
                </span>
                <span className="text-center text-xs font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400">
                  Pro
                </span>
              </div>

              {FEATURES.map((section, si) => (
                <div key={si}>
                  {/* Category row */}
                  <div className="border-b border-slate-100 bg-slate-50/60 px-6 py-2.5 dark:border-slate-800/50 dark:bg-slate-900/40">
                    <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                      {section.category}
                    </span>
                  </div>

                  {section.rows.map((row, ri) => (
                    <div
                      key={ri}
                      className={`grid grid-cols-[1fr_96px_96px] items-center px-6 py-4 ${
                        ri < section.rows.length - 1
                          ? 'border-b border-slate-100 dark:border-slate-800/60'
                          : ''
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm text-slate-700 dark:text-slate-300">
                          {row.label}
                        </span>
                        {row.hint && (
                          <span title={row.hint} className="cursor-help">
                            <HelpCircle className="h-3.5 w-3.5 text-slate-300 dark:text-slate-600" />
                          </span>
                        )}
                      </div>
                      <FeatureValue value={row.free} />
                      <FeatureValue value={row.pro} />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── FAQ ──────────────────────────────────────────────────────── */}
        <section className="px-4 pb-20 sm:px-6">
          <div className="mx-auto max-w-2xl">
            <h2 className="mb-2 text-center text-xl font-bold text-slate-900 dark:text-white">
              Frequently asked questions
            </h2>
            <p className="mb-8 text-center text-sm text-slate-500 dark:text-slate-400">
              Still have questions?{' '}
              <Link
                to="/contact"
                className="text-cyan-600 underline-offset-2 hover:underline dark:text-cyan-400"
              >
                Contact us
              </Link>
              .
            </p>

            <div className="rounded-2xl border border-slate-200 bg-white px-6 dark:border-slate-800 dark:bg-slate-900">
              {FAQ.map((item, i) => (
                <FaqItem key={i} q={item.q} a={item.a} />
              ))}
            </div>
          </div>
        </section>

        {/* ── Bottom CTA (hidden for paid users) ───────────────────────── */}
        {!isPaid && (
          <section className="px-4 pb-24 sm:px-6">
            <div className="mx-auto max-w-2xl rounded-2xl border border-cyan-200/60 bg-gradient-to-br from-cyan-50 to-slate-50 p-10 text-center dark:border-cyan-800/30 dark:from-cyan-950/20 dark:to-slate-900">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                Start analyzing NYC deals today
              </h2>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
                Free tier is permanent — no expiry, no credit card. Upgrade when your volume grows.
              </p>

              <div className="mt-6 flex flex-wrap justify-center gap-3">
                {user ? (
                  <button
                    type="button"
                    disabled={upgradeLoading}
                    onClick={() => void handleUpgrade()}
                    className="rounded-xl bg-cyan-500 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
                  >
                    {upgradeLoading ? 'Redirecting…' : 'Upgrade to Pro — $29/mo'}
                  </button>
                ) : (
                  <>
                    <Link
                      to="/register"
                      className="rounded-xl bg-cyan-500 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
                    >
                      Get started free
                    </Link>
                    <Link
                      to="/login"
                      className="rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:hover:bg-slate-800"
                    >
                      Sign in
                    </Link>
                  </>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      <Footer />
    </div>
  )
}
