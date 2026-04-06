import { dealLabelBadgeClasses } from '../utils/dealLabelBadge'

/**
 * Prominent Buy / Hold / Avoid pill for analysis cards and results headers.
 */
export default function DealLabelBadge({ label, size = 'md' }) {
  if (!label) return null
  const sizeClasses =
    size === 'sm'
      ? 'px-2.5 py-0.5 text-xs uppercase tracking-wide'
      : 'px-4 py-1.5 text-sm font-bold uppercase tracking-wider'

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border font-semibold ${sizeClasses} ${dealLabelBadgeClasses(label)}`}
    >
      {label}
    </span>
  )
}
