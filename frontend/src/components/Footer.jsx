import { Link } from 'react-router-dom'

export default function Footer() {
  const year = new Date().getFullYear()

  const legalLink =
    'text-xs font-medium text-slate-500 underline-offset-2 transition hover:text-slate-800 hover:underline dark:text-slate-400 dark:hover:text-white'

  return (
    <footer className="mt-auto border-t border-slate-200 bg-slate-50/90 dark:border-slate-800 dark:bg-gradient-to-t dark:from-slate-900/80 dark:to-slate-950">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 px-4 py-8 text-center sm:px-6">
        <nav className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1" aria-label="Legal">
          <Link to="/contact" className={legalLink}>
            Contact
          </Link>
          <Link to="/terms" className={legalLink}>
            Terms of Service
          </Link>
          <Link to="/privacy" className={legalLink}>
            Privacy Policy
          </Link>
          <Link to="/disclaimer" className={legalLink}>
            Valuation &amp; AI disclaimer
          </Link>
        </nav>
        <p className="text-xs text-slate-500 dark:text-slate-500">© {year} PropIntel AI LLC</p>
        <p className="max-w-2xl text-xs leading-relaxed text-slate-500 dark:text-slate-500">
          Estimates are for education and decision support only — not financial, legal, tax, or investment
          advice. Not a substitute for a licensed appraisal or broker.
        </p>
      </div>
    </footer>
  )
}
