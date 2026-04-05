/**
 * Prominent Buy / Hold / Avoid pill for analysis cards and results headers.
 */
export function dealLabelBadgeClasses(label) {
  const n = label?.toString().trim().toLowerCase()
  if (n === 'buy') {
    return 'border-emerald-600 bg-emerald-600 text-white shadow-sm shadow-emerald-900/20 dark:border-emerald-500 dark:bg-emerald-600'
  }
  if (n === 'hold') {
    return 'border-amber-500 bg-amber-500 text-slate-950 shadow-sm shadow-amber-900/15 dark:border-amber-400 dark:bg-amber-500 dark:text-slate-950'
  }
  return 'border-rose-600 bg-rose-600 text-white shadow-sm shadow-rose-900/20 dark:border-rose-500 dark:bg-rose-600'
}

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
