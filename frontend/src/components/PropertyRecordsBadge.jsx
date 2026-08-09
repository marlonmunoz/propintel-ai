import { BadgeCheck } from 'lucide-react'

/**
 * Small badge shown when a valuation was enhanced with resolved city
 * property records (DOF assessment, ACRIS deed history, PLUTO physical
 * data) — via either a client-supplied bbl or server-side address
 * resolution (see backend/app/services/address_resolver.py).
 *
 * Renders nothing when the backend didn't report bbl_enhanced (older
 * responses, or a valuation that had no property records to draw on).
 */
export default function PropertyRecordsBadge({ metadata, size = 'md' }) {
  if (!metadata?.bbl_enhanced) return null

  const sizeClasses = size === 'sm' ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-sm'

  const sourceNote =
    metadata.bbl_source === 'address'
      ? 'Your address was automatically matched to city property records.'
      : 'Matched to city property records.'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-600 dark:text-emerald-400 ${sizeClasses}`}
      title={`${sourceNote} This valuation uses additional DOF assessment, ACRIS deed history, and PLUTO building data for higher accuracy.`}
    >
      <BadgeCheck className="h-3.5 w-3.5 shrink-0" aria-hidden />
      Enhanced with property records
    </span>
  )
}
