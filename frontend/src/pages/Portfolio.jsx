import { useState, useEffect, useMemo } from 'react'
import { BarChart3, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import DealLabelBadge from '../components/DealLabelBadge'
import { getProperties, deleteProperty } from '../services/propertiesApi'

function formatCurrency(value) {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value) {
  if (value == null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

const DEAL_LABELS = ['All', 'Buy', 'Hold', 'Avoid']

const SORT_OPTIONS = [
  { value: 'default', label: 'Date saved' },
  { value: 'score_desc', label: 'Score: High → Low' },
  { value: 'score_asc', label: 'Score: Low → High' },
  { value: 'roi_desc', label: 'ROI: High → Low' },
  { value: 'predicted_desc', label: 'Predicted Price: High → Low' },
]

function filterChipClasses(label, active) {
  if (active) {
    if (label === 'Buy') return 'border-emerald-500 bg-emerald-500 text-white'
    if (label === 'Hold') return 'border-amber-500 bg-amber-500 text-white'
    if (label === 'Avoid') return 'border-rose-500 bg-rose-500 text-white'
    return 'border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-950'
  }
  if (label === 'Buy') return 'border-emerald-500/40 text-emerald-700 hover:bg-emerald-500/10 dark:text-emerald-400'
  if (label === 'Hold') return 'border-amber-500/40 text-amber-700 hover:bg-amber-500/10 dark:text-amber-400'
  if (label === 'Avoid') return 'border-rose-500/40 text-rose-700 hover:bg-rose-500/10 dark:text-rose-400'
  return 'border-slate-300 text-slate-600 hover:border-slate-400 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:bg-slate-800'
}

export default function Portfolio() {
  const [properties, setProperties] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [filterLabel, setFilterLabel] = useState('All')
  const [sortBy, setSortBy] = useState('default')

  useEffect(() => {
    fetchProperties()
  }, [])

  async function fetchProperties() {
    setIsLoading(true)
    setError('')
    try {
      const data = await getProperties({ limit: 50 })
      setProperties(data)
    } catch (err) {
      setError(err.message || 'Failed to load saved analyses.')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleDelete(id) {
    try {
      await deleteProperty(id)
      setProperties((prev) => prev.filter((p) => p.id !== id))
      setConfirmDeleteId(null)
    } catch (err) {
      setError(err.message || 'Failed to delete.')
      setConfirmDeleteId(null)
    }
  }

  // Derived list — computed from properties + filterLabel + sortBy.
  // useMemo caches the result and only recomputes when one of those three changes.
  const visibleProperties = useMemo(() => {
    let result = [...properties]

    // Filter by deal label
    if (filterLabel !== 'All') {
      result = result.filter(
        (p) => p.analysis?.investment_analysis?.deal_label === filterLabel
      )
    }

    // Sort
    if (sortBy === 'default') {
      // Newest saved first. created_at is present after the DB migration;
      // fall back to id desc so pre-migration rows still sort reasonably.
      result.sort((a, b) => {
        if (a.created_at && b.created_at) {
          return new Date(b.created_at) - new Date(a.created_at)
        }
        return b.id - a.id
      })
    } else if (sortBy === 'score_desc') {
      result.sort(
        (a, b) =>
          (b.analysis?.investment_analysis?.investment_score ?? -1) -
          (a.analysis?.investment_analysis?.investment_score ?? -1)
      )
    } else if (sortBy === 'score_asc') {
      result.sort(
        (a, b) =>
          (a.analysis?.investment_analysis?.investment_score ?? 101) -
          (b.analysis?.investment_analysis?.investment_score ?? 101)
      )
    } else if (sortBy === 'roi_desc') {
      result.sort(
        (a, b) =>
          (b.analysis?.investment_analysis?.roi_estimate ?? -Infinity) -
          (a.analysis?.investment_analysis?.roi_estimate ?? -Infinity)
      )
    } else if (sortBy === 'predicted_desc') {
      result.sort(
        (a, b) =>
          (b.analysis?.valuation?.predicted_price ?? 0) -
          (a.analysis?.valuation?.predicted_price ?? 0)
      )
    }

    return result
  }, [properties, filterLabel, sortBy])

  const isFiltered = filterLabel !== 'All'

  return (
    <div className="min-h-screen bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <section className="mx-auto max-w-6xl px-6 pb-16 pt-24">

        {/* Header */}
        <div className="mb-6">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">
            Portfolio
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">Saved Analyses</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Properties you analyzed and saved — no need to re-run the model.
          </p>
        </div>

        {/* Toolbar — filter chips + sort */}
        {!isLoading && properties.length > 0 && (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            {/* Filter chips */}
            <div className="flex flex-wrap items-center gap-2">
              {DEAL_LABELS.map((label) => (
                <button
                  key={label}
                  onClick={() => setFilterLabel(label)}
                  className={`rounded-full border px-3 py-1 text-sm font-semibold transition ${filterChipClasses(label, filterLabel === label)}`}
                >
                  {label}
                </button>
              ))}
              {isFiltered && (
                <span className="text-sm text-slate-400 dark:text-slate-500">
                  {visibleProperties.length} of {properties.length}
                </span>
              )}
            </div>

            {/* Sort dropdown */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 outline-none transition focus:border-cyan-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:focus:border-cyan-400"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-600 dark:text-rose-400">
            {error}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20 text-slate-400">
            Loading…
          </div>
        )}

        {/* Empty state — no properties at all */}
        {!isLoading && !error && properties.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 py-20 text-center dark:border-slate-700">
            <BarChart3 className="mb-4 h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p className="text-lg font-semibold text-slate-700 dark:text-slate-300">No saved analyses yet</p>
            <p className="mt-1 text-sm text-slate-400 dark:text-slate-500">
              Run an analysis and click{' '}
              <span className="font-medium text-slate-900 dark:text-white">Save to Portfolio</span>{' '}
              to store it here.
            </p>
            <Link
              to="/analyze"
              className="mt-6 rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
            >
              Go to Analyze
            </Link>
          </div>
        )}

        {/* Empty state — filter returned no results */}
        {!isLoading && properties.length > 0 && visibleProperties.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 py-16 text-center dark:border-slate-700">
            <p className="text-base font-semibold text-slate-700 dark:text-slate-300">
              No <span className="text-slate-900 dark:text-white">{filterLabel}</span> analyses in your portfolio
            </p>
            <button
              onClick={() => setFilterLabel('All')}
              className="mt-4 text-sm font-semibold text-cyan-600 transition hover:text-cyan-500 dark:text-cyan-400"
            >
              Clear filter
            </button>
          </div>
        )}

        {/* Analysis cards */}
        {!isLoading && visibleProperties.length > 0 && (
          <div className="space-y-4">
            {visibleProperties.map((property) => {
              const a = property.analysis
              const valuation = a?.valuation
              const inv = a?.investment_analysis
              const exp = a?.explanation
              const isExpanded = expandedId === property.id

              return (
                <div
                  key={property.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50 transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-slate-600"
                >
                  {/* Card header — always visible */}
                  <div className="flex flex-wrap items-center justify-between gap-4 p-5">
                    <div className="flex items-center gap-4">
                      <span className="flex h-7 min-w-[28px] flex-shrink-0 items-center justify-center rounded-lg bg-slate-200 px-1.5 text-xs font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        {property.id}
                      </span>
                      <div>
                        <p className="font-semibold text-slate-900 dark:text-white">{property.address}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          {inv?.deal_label ? <DealLabelBadge label={inv.deal_label} size="sm" /> : null}
                          {inv?.investment_score != null ? (
                            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                              Score {inv.investment_score}/100
                            </span>
                          ) : null}
                          {property.created_at && (
                            <span className="text-xs text-slate-400 dark:text-slate-500">
                              Saved {new Date(property.created_at).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-6 text-sm">
                      {valuation && (
                        <>
                          <div className="text-right">
                            <p className="text-xs text-slate-400 dark:text-slate-500">Predicted</p>
                            <p className="font-semibold text-cyan-600 dark:text-cyan-400">
                              {formatCurrency(valuation.predicted_price)}
                            </p>
                            {valuation.price_low != null && valuation.price_high != null ? (
                              <p className="mt-0.5 max-w-[11rem] text-right text-[10px] leading-tight text-slate-400 dark:text-slate-500">
                                Range {formatCurrency(valuation.price_low)} –{' '}
                                {formatCurrency(valuation.price_high)}
                              </p>
                            ) : null}
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-400 dark:text-slate-500">Market</p>
                            <p className="font-semibold text-slate-900 dark:text-white">
                              {formatCurrency(valuation.market_price)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-400 dark:text-slate-500">Difference</p>
                            <p className={`font-semibold ${valuation.price_difference >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                              {formatPercent(valuation.price_difference_pct)}
                            </p>
                          </div>
                        </>
                      )}
                      {inv && (
                        <div className="text-right">
                          <p className="text-xs text-slate-400 dark:text-slate-500">ROI Est.</p>
                          <p className="font-semibold text-slate-900 dark:text-white">
                            {formatPercent(inv.roi_estimate)}
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {a && (
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : property.id)}
                          className="rounded-xl border border-slate-300 px-3 py-1.5 text-sm text-slate-600 transition hover:border-slate-400 hover:text-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:text-white"
                        >
                          {isExpanded ? 'Collapse' : 'Details'}
                        </button>
                      )}
                      {confirmDeleteId === property.id ? (
                        <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-1.5">
                          <span className="text-sm text-rose-600 dark:text-rose-300">Delete?</span>
                          <button
                            onClick={() => handleDelete(property.id)}
                            className="text-sm font-semibold text-rose-500 transition hover:text-rose-400 dark:text-rose-400 dark:hover:text-rose-300"
                          >
                            Yes
                          </button>
                          <span className="text-slate-300 dark:text-slate-600">·</span>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="text-sm font-semibold text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDeleteId(property.id)}
                          className="flex items-center gap-1 rounded-xl border border-rose-500/30 px-3 py-1.5 text-sm text-rose-500 transition hover:bg-rose-500/10 dark:text-rose-400"
                        >
                          <Trash2 className="h-3.5 w-3.5" /> Delete
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expanded details */}
                  {isExpanded && a && (
                    <div className="space-y-4 border-t border-slate-200 px-5 pb-5 pt-4 dark:border-slate-800">
                      {inv?.recommendation && (
                        <p className="text-sm text-slate-600 dark:text-slate-300">
                          <span className="font-semibold text-slate-900 dark:text-white">Recommendation: </span>
                          {inv.recommendation}
                        </p>
                      )}
                      {inv?.analysis_summary && (
                        <p className="text-sm leading-7 text-slate-600 dark:text-slate-300">
                          {inv.analysis_summary}
                        </p>
                      )}
                      {exp && (
                        <div className="grid gap-3 sm:grid-cols-3">
                          {exp.summary && (
                            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Summary</p>
                              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{exp.summary}</p>
                            </div>
                          )}
                          {exp.opportunity && (
                            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Opportunity</p>
                              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{exp.opportunity}</p>
                            </div>
                          )}
                          {exp.risks && (
                            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Risks</p>
                              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{exp.risks}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
