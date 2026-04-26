import { useState, useEffect, useMemo } from 'react'
import { BarChart3, FileDown, FileSpreadsheet, Printer, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import DealLabelBadge from '../components/DealLabelBadge'
import { useAuth } from '../context/AuthContext'
import { getProperties, deleteProperty } from '../services/propertiesApi'
import { downloadPropertyCsv, downloadPropertyPdf } from '../utils/portfolioReportExport'
import { printPortfolioReport } from '../utils/portfolioReportPrint'

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

function dealLabelHeaderClasses(label) {
  const l = (label || '').toLowerCase()
  if (l === 'buy')
    return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:border-emerald-400/40 dark:bg-emerald-400/10 dark:text-emerald-200'
  if (l === 'hold')
    return 'border-amber-500/40 bg-amber-500/10 text-amber-800 dark:border-amber-400/40 dark:bg-amber-400/10 dark:text-amber-200'
  if (l === 'avoid')
    return 'border-rose-500/40 bg-rose-500/10 text-rose-700 dark:border-rose-400/40 dark:bg-rose-400/10 dark:text-rose-200'
  return 'border-slate-300/60 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
}

function getCompareLimit(profile) {
  const role = profile?.role
  if (role === 'paid' || role === 'admin') return 10
  return 2
}

function formatDateShort(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

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
  const { refreshProfile, profile } = useAuth()
  const [properties, setProperties] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [filterLabel, setFilterLabel] = useState('All')
  const [sortBy, setSortBy] = useState('default')
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [selectedOrder, setSelectedOrder] = useState([])
  const [compareOpen, setCompareOpen] = useState(false)
  const [compareError, setCompareError] = useState('')

  useEffect(() => {
    fetchProperties()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional mount-only load; fetchProperties is stable enough for initial fetch
  }, [])

  async function fetchProperties() {
    setIsLoading(true)
    setError('')
    try {
      await refreshProfile()
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
  const compareLimit = getCompareLimit(profile)
  const selectedCount = selectedOrder.length
  const canCompare = selectedCount >= 2

  const selectedProperties = useMemo(() => {
    const map = new Map(properties.map((p) => [String(p.id), p]))
    return selectedOrder.map((id) => map.get(String(id))).filter(Boolean)
  }, [properties, selectedOrder])

  function clearSelection() {
    setSelectedIds(new Set())
    setSelectedOrder([])
    setCompareError('')
    setCompareOpen(false)
  }

  function toggleSelected(propertyId) {
    const id = String(propertyId)
    setCompareError('')
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    setSelectedOrder((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= compareLimit) {
        setCompareError(
          compareLimit === 2
            ? 'Free tier: compare up to 2. Upgrade to compare up to 10.'
            : `Compare limit reached (${compareLimit}).`
        )
        return prev
      }
      return [...prev, id]
    })
  }

  function openCompare() {
    setCompareError('')
    if (!canCompare) return
    setCompareOpen(true)
  }

  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <section className="mx-auto flex-1 max-w-6xl px-6 pb-16 pt-24">

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
              const id = String(property.id)
              const isSelected = selectedIds.has(id)
              const disableUnchecked = !isSelected && selectedCount >= compareLimit

              return (
                <div
                  key={property.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50 transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-slate-600"
                >
                  {/* Card header — always visible */}
                  <div className="space-y-4 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex min-w-0 items-center gap-4">
                        <label
                          className={`flex items-center gap-2 rounded-lg border px-2 py-1 text-xs font-semibold ${
                            isSelected
                              ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-900 dark:border-cyan-400/50 dark:bg-cyan-400/10 dark:text-cyan-200'
                              : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300 dark:hover:border-slate-600'
                          } ${disableUnchecked ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                          title={
                            disableUnchecked
                              ? compareLimit === 2
                                ? 'Free tier: compare up to 2. Upgrade to compare up to 10.'
                                : `Compare limit reached (${compareLimit}).`
                              : 'Select for comparison'
                          }
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            disabled={disableUnchecked}
                            onChange={() => toggleSelected(property.id)}
                            aria-label={`Select ${property.address} for comparison`}
                            className="h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 dark:border-slate-700 dark:bg-slate-900"
                          />
                          Compare
                        </label>
                        <span className="flex h-7 min-w-[28px] flex-shrink-0 items-center justify-center rounded-lg bg-slate-200 px-1.5 text-xs font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                          {property.id}
                        </span>
                        <div className="min-w-0">
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
                    </div>

                    <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
                      <div className="flex flex-wrap items-center gap-2">
                        {a && (
                          <>
                            <button
                              type="button"
                              onClick={() => printPortfolioReport(property)}
                              className="flex items-center gap-1.5 rounded-xl border border-sky-400/60 bg-sky-500/10 px-3 py-1.5 text-sm font-medium text-sky-800 transition hover:border-sky-500 hover:bg-sky-500/15 dark:border-sky-400/50 dark:bg-sky-400/10 dark:text-sky-200 dark:hover:border-sky-300 dark:hover:bg-sky-400/20"
                              aria-label="Print report"
                              title="Print report"
                            >
                              <Printer className="h-3.5 w-3.5 shrink-0" />
                              Print
                            </button>
                            <button
                              type="button"
                              onClick={() => void downloadPropertyPdf(property)}
                              className="flex items-center gap-1.5 rounded-xl border border-rose-400/60 bg-rose-500/10 px-3 py-1.5 text-sm font-medium text-rose-800 transition hover:border-rose-500 hover:bg-rose-500/15 dark:border-rose-400/50 dark:bg-rose-400/10 dark:text-rose-200 dark:hover:border-rose-300 dark:hover:bg-rose-400/20"
                              aria-label="Download PDF"
                              title="Download PDF"
                            >
                              <FileDown className="h-3.5 w-3.5 shrink-0" />
                              PDF
                            </button>
                            <button
                              type="button"
                              onClick={() => downloadPropertyCsv(property)}
                              className="flex items-center gap-1.5 rounded-xl border border-emerald-400/60 bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-900 transition hover:border-emerald-500 hover:bg-emerald-500/15 dark:border-emerald-400/50 dark:bg-emerald-400/10 dark:text-emerald-200 dark:hover:border-emerald-300 dark:hover:bg-emerald-400/20"
                              aria-label="Download CSV"
                              title="Download CSV"
                            >
                              <FileSpreadsheet className="h-3.5 w-3.5 shrink-0" />
                              CSV
                            </button>
                          </>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {a && (
                          <button
                            type="button"
                            onClick={() => setExpandedId(isExpanded ? null : property.id)}
                            className="rounded-xl border border-cyan-500/50 bg-cyan-500/10 px-3 py-1.5 text-sm font-medium text-cyan-900 transition hover:border-cyan-500 hover:bg-cyan-500/15 dark:border-cyan-400/50 dark:bg-cyan-400/10 dark:text-cyan-300 dark:hover:border-cyan-300 dark:hover:bg-cyan-400/20"
                          >
                            {isExpanded ? 'Collapse' : 'Details'}
                          </button>
                        )}
                        {confirmDeleteId === property.id ? (
                          <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-1.5">
                            <span className="text-sm text-rose-600 dark:text-rose-300">Delete?</span>
                            <button
                              type="button"
                              onClick={() => handleDelete(property.id)}
                              className="text-sm font-semibold text-rose-500 transition hover:text-rose-400 dark:text-rose-400 dark:hover:text-rose-300"
                            >
                              Yes
                            </button>
                            <span className="text-slate-300 dark:text-slate-600">·</span>
                            <button
                              type="button"
                              onClick={() => setConfirmDeleteId(null)}
                              className="text-sm font-semibold text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(property.id)}
                            className="flex items-center gap-1 rounded-xl border border-rose-500/30 px-3 py-1.5 text-sm text-rose-500 transition hover:bg-rose-500/10 dark:text-rose-400"
                          >
                            <Trash2 className="h-3.5 w-3.5" /> Delete
                          </button>
                        )}
                      </div>
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

      {/* Sticky compare bar */}
      {selectedCount > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900 dark:text-white">
                {canCompare ? (
                  <>
                    Compare <span className="text-cyan-600 dark:text-cyan-400">{selectedCount}</span>{' '}
                    properties — <span className="text-slate-500 dark:text-slate-400">no quota used</span>
                  </>
                ) : (
                  <>
                    Select <span className="text-cyan-600 dark:text-cyan-400">2+</span> properties to compare
                  </>
                )}
              </p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Limit: {compareLimit}. {profile?.role === 'user' ? 'Free tier compares up to 2 · Paid compares up to 10.' : ''}
              </p>
              {compareError && (
                <p className="mt-1 text-xs font-semibold text-rose-600 dark:text-rose-400">{compareError}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={clearSelection}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={openCompare}
                disabled={!canCompare}
                className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  canCompare
                    ? 'bg-cyan-500 text-slate-950 hover:bg-cyan-400'
                    : 'cursor-not-allowed bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                }`}
              >
                Compare {selectedCount} properties →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Compare slide-in panel */}
      {compareOpen && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/40"
            aria-label="Close comparison"
            onClick={() => setCompareOpen(false)}
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Compare properties"
            className="absolute right-0 top-0 h-full w-full max-w-5xl overflow-hidden border-l border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950"
          >
            <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">
                  Comparison
                </p>
                <h2 className="mt-1 text-xl font-bold text-slate-900 dark:text-white">
                  Compare saved analyses — no quota used
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Side-by-side snapshot from your portfolio (free).
                </p>
              </div>
              <button
                type="button"
                onClick={() => setCompareOpen(false)}
                className="rounded-xl border border-slate-300 bg-white p-2 text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="h-[calc(100%-80px)] overflow-auto p-6">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse">
                  <thead>
                    <tr>
                      <th className="sticky left-0 z-10 bg-white px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-950 dark:text-slate-400">
                        Metric
                      </th>
                      {selectedProperties.map((p) => {
                        const inv = p?.analysis?.investment_analysis
                        const label = inv?.deal_label
                        return (
                          <th key={p.id} className="px-3 py-2 text-left">
                            <div className={`rounded-xl border px-3 py-2 ${dealLabelHeaderClasses(label)}`}>
                              <p className="truncate text-sm font-semibold">{p.address}</p>
                              <div className="mt-1 flex flex-wrap items-center gap-2">
                                {label ? <DealLabelBadge label={label} size="sm" /> : null}
                                {p.created_at ? (
                                  <span className="text-xs opacity-80">Saved {formatDateShort(p.created_at)}</span>
                                ) : null}
                              </div>
                            </div>
                          </th>
                        )
                      })}
                    </tr>
                  </thead>
                  <tbody className="align-top">
                    {(() => {
                      const rows = [
                        { key: 'deal', label: 'Deal Label' },
                        { key: 'predicted', label: 'Predicted Price', dir: 'max' },
                        { key: 'market', label: 'Market Price', dir: 'min' },
                        { key: 'roi', label: 'ROI Est.', dir: 'max' },
                        { key: 'score', label: 'Investment Score', dir: 'max' },
                        { key: 'diff', label: 'Price Difference', dir: 'max' },
                        { key: 'saved', label: 'Saved', dir: 'max' },
                      ]

                      function getNumeric(rowKey, p) {
                        const a = p?.analysis
                        const v = a?.valuation
                        const inv = a?.investment_analysis
                        if (rowKey === 'predicted') return v?.predicted_price ?? null
                        if (rowKey === 'market') return v?.market_price ?? null
                        if (rowKey === 'roi') return inv?.roi_estimate ?? null
                        if (rowKey === 'score') return inv?.investment_score ?? null
                        if (rowKey === 'diff') return v?.price_difference ?? null
                        if (rowKey === 'saved') return p?.created_at ? new Date(p.created_at).getTime() : null
                        return null
                      }

                      function formatCell(rowKey, p) {
                        const a = p?.analysis
                        const v = a?.valuation
                        const inv = a?.investment_analysis
                        if (rowKey === 'deal') return inv?.deal_label ?? '—'
                        if (rowKey === 'predicted') return formatCurrency(v?.predicted_price)
                        if (rowKey === 'market') return formatCurrency(v?.market_price)
                        if (rowKey === 'roi') return formatPercent(inv?.roi_estimate ?? null)
                        if (rowKey === 'score')
                          return inv?.investment_score != null ? `${inv.investment_score}/100` : '—'
                        if (rowKey === 'diff')
                          return v?.price_difference != null ? formatCurrency(v.price_difference) : '—'
                        if (rowKey === 'saved') return formatDateShort(p?.created_at)
                        return '—'
                      }

                      return rows.map((r, idx) => {
                        let bestIndex = -1
                        if (r.dir) {
                          const vals = selectedProperties.map((p) => getNumeric(r.key, p))
                          const filtered = vals
                            .map((v, i) => ({ v, i }))
                            .filter((x) => x.v != null && Number.isFinite(Number(x.v)))
                          if (filtered.length) {
                            filtered.sort((a, b) => (r.dir === 'min' ? a.v - b.v : b.v - a.v))
                            bestIndex = filtered[0].i
                          }
                        }

                        return (
                          <tr
                            key={r.key}
                            className={idx % 2 === 0 ? 'bg-slate-50/60 dark:bg-slate-900/20' : ''}
                          >
                            <td className="sticky left-0 z-10 border-t border-slate-200 bg-inherit px-3 py-3 text-sm font-semibold text-slate-700 dark:border-slate-800 dark:text-slate-200">
                              {r.label}
                            </td>
                            {selectedProperties.map((p, colIdx) => {
                              const highlight = bestIndex === colIdx
                              return (
                                <td
                                  key={p.id}
                                  className={`border-t border-slate-200 px-3 py-3 text-sm text-slate-700 dark:border-slate-800 dark:text-slate-200 ${
                                    highlight ? 'bg-cyan-500/10 font-semibold' : ''
                                  }`}
                                >
                                  {formatCell(r.key, p)}
                                </td>
                              )
                            })}
                          </tr>
                        )
                      })
                    })()}
                  </tbody>
                </table>
              </div>
            </div>
          </aside>
        </div>
      )}

      <Footer />
    </div>
  )
}
