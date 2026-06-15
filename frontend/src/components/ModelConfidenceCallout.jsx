import ModelConfidenceBadge from './ModelConfidenceBadge'
import { modelConfidenceCalloutClasses } from '../utils/modelConfidence'

/**
 * Explains how strongly to trust the segment valuation.
 */
export default function ModelConfidenceCallout({ metadata }) {
  const tier = metadata?.model_confidence_tier
  const note = metadata?.model_confidence_note
  const segmentLabel = metadata?.segment_label

  if (!tier || !note) return null

  return (
    <div
      className={`rounded-2xl border p-5 ${modelConfidenceCalloutClasses(tier)}`}
      role="note"
      aria-label="Model confidence"
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
          Valuation confidence
        </p>
        <ModelConfidenceBadge metadata={metadata} size="sm" />
        {segmentLabel ? (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            · {segmentLabel} model
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
        {note}
      </p>
    </div>
  )
}
