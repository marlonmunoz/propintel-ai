import { modelConfidenceBadgeClasses } from '../utils/modelConfidence'

/**
 * Pill badge for segment valuation confidence (high / directional / fallback).
 */
export default function ModelConfidenceBadge({ metadata, size = 'md' }) {
  const label = metadata?.model_confidence_label
  const tier = metadata?.model_confidence_tier
  if (!label || !tier) return null

  const sizeClasses =
    size === 'sm'
      ? 'px-2.5 py-0.5 text-xs'
      : 'px-3 py-1 text-sm'

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border font-semibold ${sizeClasses} ${modelConfidenceBadgeClasses(tier)}`}
      title={metadata?.model_confidence_note || label}
    >
      {label}
    </span>
  )
}
