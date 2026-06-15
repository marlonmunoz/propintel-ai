/**
 * Tailwind classes for model-confidence tier badges.
 */
export function modelConfidenceBadgeClasses(tier) {
  switch (tier) {
    case 'high':
      return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300'
    case 'directional':
      return 'border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300'
    case 'fallback':
    default:
      return 'border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300'
  }
}

/**
 * Border/background for the explanatory callout card.
 */
export function modelConfidenceCalloutClasses(tier) {
  switch (tier) {
    case 'high':
      return 'border-emerald-500/25 bg-emerald-500/5 dark:border-emerald-500/30 dark:bg-emerald-950/20'
    case 'directional':
      return 'border-amber-500/30 bg-amber-500/5 dark:border-amber-500/35 dark:bg-amber-950/20'
    case 'fallback':
    default:
      return 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50'
  }
}
