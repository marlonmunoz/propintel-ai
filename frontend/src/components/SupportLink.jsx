const SUPPORT_EMAIL = 'support@propintel-ai.com'

/**
 * Centralized mailto link for the customer support address.
 * Use this everywhere instead of duplicating the email string so a future change
 * (e.g. moving to a help-desk URL) only needs one edit.
 */
export default function SupportLink({
  subject,
  body,
  children,
  className = 'font-medium text-cyan-600 underline hover:text-cyan-500 dark:text-cyan-400',
}) {
  const params = []
  if (subject) params.push(`subject=${encodeURIComponent(subject)}`)
  if (body) params.push(`body=${encodeURIComponent(body)}`)
  const href = `mailto:${SUPPORT_EMAIL}${params.length ? `?${params.join('&')}` : ''}`

  return (
    <a href={href} className={className}>
      {children ?? SUPPORT_EMAIL}
    </a>
  )
}

export { SUPPORT_EMAIL }
