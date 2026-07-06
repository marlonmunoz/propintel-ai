import { Link } from 'react-router-dom'
import { BookmarkPlus, CheckCircle2, Crown, Sparkles } from 'lucide-react'
import DealLabelBadge from './DealLabelBadge'
import ModelConfidenceBadge from './ModelConfidenceBadge'
import ModelConfidenceCallout from './ModelConfidenceCallout'

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value) {
  return `${value.toFixed(2)}%`
}


function StatCard({ label, value, tone = 'default' }) {
  const toneClasses =
    tone === 'positive'
      ? 'border-emerald-500/20 bg-emerald-500/10'
      : tone === 'negative'
        ? 'border-rose-500/20 bg-rose-500/10'
        : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950'

  return (
    <div className={`rounded-xl border p-4 ${toneClasses}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-xl font-bold text-slate-900 dark:text-white">{value}</p>
    </div>
  )
}

function isQuotaExhaustedExplanation(result) {
  if (result?.explanation_status === 'quota_exhausted') return true
  const s = result?.explanation?.summary
  return typeof s === 'string' && s.startsWith('Daily AI explanation quota reached')
}

/**
 * Right panel of the Analyze page — analysis results display.
 *
 * Purely presentational: renders whatever props it receives and fires the
 * onSaveToPortfolio callback.  All state lives in the parent (Analyze.jsx).
 */
export default function AnalyzeResults({
  analysisResult,
  hasV2Result,
  isLoading,
  isExplanationLoading,
  explanationError,
  score,
  scoreCategory,
  dealLabel,
  difference,
  isSaving,
  savedToPortfolio,
  saveError,
  onSaveToPortfolio,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Analysis Results</h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Real backend results appear here after the analysis request completes.
          </p>
        </div>

        {hasV2Result ? (
          <div className="flex flex-wrap items-center gap-3">
            <DealLabelBadge label={dealLabel} />
            <ModelConfidenceBadge metadata={analysisResult.metadata} />
            {score !== undefined && score !== null ? (
              <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                Investment score <span className="text-slate-900 dark:text-white">{score}</span>
                /100
              </span>
            ) : null}
          </div>
        ) : null}
      </div>

      {!analysisResult && !isLoading ? (
        <div className="mt-6 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
          Submit the form to fetch valuation, investment score, drivers,
          and explanation from the v2 backend.
        </div>
      ) : null}

      {/* Loading skeleton — visible while the fast ML call is in flight */}
      {isLoading ? (
        <div className="mt-6 animate-pulse space-y-4" aria-busy="true" aria-label="Loading analysis">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
                <div className="h-3 w-24 rounded bg-slate-200 dark:bg-slate-700" />
                <div className="mt-3 h-7 w-32 rounded bg-slate-200 dark:bg-slate-700" />
              </div>
            ))}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <div className="h-3 w-40 rounded bg-slate-200 dark:bg-slate-700" />
            <div className="mt-3 h-8 w-56 rounded bg-slate-200 dark:bg-slate-700" />
            <div className="mt-2 h-3 w-72 rounded bg-slate-200 dark:bg-slate-700" />
          </div>
          <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <div className="h-3 w-28 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="mt-4 h-14 w-16 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="mt-4 h-6 w-24 rounded-full bg-slate-200 dark:bg-slate-700" />
            </div>
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <div className="h-3 w-32 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="h-4 w-full rounded bg-slate-200 dark:bg-slate-700" />
              <div className="h-4 w-5/6 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="h-4 w-4/6 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="mt-1 h-4 w-full rounded bg-slate-200 dark:bg-slate-700" />
              <div className="h-4 w-3/4 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="h-4 w-5/6 rounded bg-slate-200 dark:bg-slate-700" />
            </div>
          </div>
        </div>
      ) : null}

      {analysisResult && !hasV2Result && !isLoading ? (
        <div className="mt-6 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-200">
          The API returned a response, but it did not match the expected
          v2 grouped shape. Open the browser console and inspect
          <span className="mx-1 font-semibold text-slate-900 dark:text-white">
            API result:
          </span>
          to verify what the backend returned.
        </div>
      ) : null}

      {hasV2Result ? (
        <div className="mt-6 space-y-6">
          {/* Stat cards */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Predicted Value"
              value={formatCurrency(analysisResult.valuation.predicted_price)}
            />
            <StatCard
              label="Market Price"
              value={formatCurrency(analysisResult.valuation.market_price)}
            />
            <StatCard
              label="Price Difference"
              value={formatCurrency(analysisResult.valuation.price_difference)}
              tone={difference >= 0 ? 'positive' : 'negative'}
            />
            <StatCard
              label="Difference %"
              value={formatPercent(analysisResult.valuation.price_difference_pct)}
              tone={analysisResult.valuation.price_difference_pct >= 0 ? 'positive' : 'negative'}
            />
          </div>

          <ModelConfidenceCallout metadata={analysisResult.metadata} />

          {/* Valuation range */}
          {analysisResult.valuation.price_low != null &&
          analysisResult.valuation.price_high != null ? (
            <div className="rounded-2xl border border-cyan-500/25 bg-cyan-500/5 p-5 dark:border-cyan-500/30 dark:bg-cyan-950/30">
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700 dark:text-cyan-400">
                Estimated valuation range
              </p>
              <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                {formatCurrency(analysisResult.valuation.price_low)}
                <span className="mx-2 font-normal text-slate-400 dark:text-slate-500">–</span>
                {formatCurrency(analysisResult.valuation.price_high)}
              </p>
              {analysisResult.valuation.valuation_interval_note ? (
                <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  {analysisResult.valuation.valuation_interval_note}
                </p>
              ) : null}
            </div>
          ) : null}

          {/* Investment score + summary */}
          <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Investment Score
              </p>
              <p className="mt-4 text-5xl font-bold text-slate-900 dark:text-white">
                {score}/100
              </p>
              {scoreCategory ? (
                <div className={`mt-4 inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${scoreCategory.classes}`}>
                  {scoreCategory.label}
                </div>
              ) : null}
              <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
                Confidence:{' '}
                <span className="font-semibold text-slate-900 dark:text-white">
                  {analysisResult.investment_analysis.confidence}
                </span>
              </p>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Recommendation:{' '}
                <span className="font-semibold text-slate-900 dark:text-white">
                  {analysisResult.investment_analysis.recommendation}
                </span>
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                Investment Summary
              </p>
              <p className="mt-4 text-base leading-7 text-slate-700 dark:text-slate-200">
                {analysisResult.investment_analysis.analysis_summary}
              </p>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    ROI Estimate
                  </p>
                  <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
                    {formatPercent(analysisResult.investment_analysis.roi_estimate)}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Segment Model
                  </p>
                  <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
                    {analysisResult.metadata.segment_label || analysisResult.metadata.segment || '—'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    v{analysisResult.metadata.model_version || '—'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Drivers */}
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                Top Drivers
              </h3>
              <ul className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                {analysisResult.drivers.top_drivers.map((driver) => (
                  <li
                    key={driver}
                    className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70"
                  >
                    {driver}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                Model Context
              </h3>
              <ul className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                {analysisResult.drivers.global_context.map((item) => (
                  <li
                    key={item}
                    className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* AI Explanation */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center gap-2">
              <Sparkles className={`h-5 w-5 text-amber-400 drop-shadow-[0_0_10px_rgba(252,211,77,0.35)] ${isExplanationLoading ? 'animate-pulse' : ''}`} />
              <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">
                AI Explanation
              </h3>
              {isExplanationLoading && (
                <span className="ml-1 text-xs text-slate-400 dark:text-slate-500">
                  Generating…
                </span>
              )}
            </div>

            {isExplanationLoading ? (
              <div className="mt-4 animate-pulse grid gap-4 xl:grid-cols-3">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70 space-y-3"
                  >
                    <div className="h-3 w-16 rounded bg-slate-200 dark:bg-slate-700" />
                    <div className="h-4 w-full rounded bg-slate-200 dark:bg-slate-700" />
                    <div className="h-4 w-5/6 rounded bg-slate-200 dark:bg-slate-700" />
                    <div className="h-4 w-4/6 rounded bg-slate-200 dark:bg-slate-700" />
                    <div className="h-4 w-full rounded bg-slate-200 dark:bg-slate-700" />
                  </div>
                ))}
              </div>
            ) : explanationError ? (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600 dark:border-rose-800/50 dark:bg-rose-950/20 dark:text-rose-400">
                {explanationError}
              </div>
            ) : isQuotaExhaustedExplanation(analysisResult) ? (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-800/50 dark:bg-amber-950/20">
                <div className="flex items-start gap-3">
                  <Crown className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-white">
                      Daily AI quota reached
                    </p>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                      You&apos;ve used all your AI-powered explanation calls for today. The
                      valuation, score, and drivers above are still accurate — only the
                      narrative explanation is unavailable until your quota resets.
                    </p>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <Link
                        to="/profile"
                        className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400"
                      >
                        <Crown className="h-4 w-4" />
                        Upgrade on Profile page
                      </Link>
                      <p className="text-xs text-slate-400 dark:text-slate-500">
                        Quota resets daily at midnight UTC
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4 grid gap-4 xl:grid-cols-3">
                {[
                  { label: 'Summary',     text: analysisResult.explanation.summary,     locked: false },
                  { label: 'Opportunity', text: analysisResult.explanation.opportunity, locked: analysisResult.explanation.narrative_locked },
                  { label: 'Risks',       text: analysisResult.explanation.risks,       locked: analysisResult.explanation.narrative_locked },
                ].map(({ label, text, locked }) => (
                  <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/70">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        {label}
                      </p>
                      {locked && (
                        <Crown className="h-3.5 w-3.5 shrink-0 text-cyan-500/70" aria-hidden />
                      )}
                    </div>
                    <p className="mt-3 text-sm leading-7 text-slate-600 dark:text-slate-300">
                      {text}
                    </p>
                    {locked && (
                      <Link
                        to="/pricing"
                        className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700 transition hover:bg-cyan-100 dark:border-cyan-800/50 dark:bg-cyan-950/30 dark:text-cyan-300 dark:hover:bg-cyan-950/50"
                      >
                        <Crown className="h-3 w-3" />
                        Unlock full analysis with Pro
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Save to Portfolio */}
          <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 dark:border-slate-800 dark:bg-slate-950">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Save to Portfolio</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Store this analysis so you can review it later without re-running the model.
              </p>
            </div>
            {savedToPortfolio ? (
              <div className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                Saved
              </div>
            ) : (
              <button
                onClick={onSaveToPortfolio}
                disabled={isSaving}
                className="flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
              >
                <BookmarkPlus className="h-4 w-4" />
                {isSaving ? 'Saving…' : 'Save'}
              </button>
            )}
          </div>
          {saveError ? (
            <p className="text-sm text-rose-500 dark:text-rose-400">{saveError}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
