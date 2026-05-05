import Navbar from './Navbar'
import Footer from './Footer'

/**
 * Wraps public legal / policy pages with consistent chrome.
 * Copy is informational — have counsel review before charging customers (especially NY / real estate).
 */
export default function LegalPageShell({ title, lastUpdated, children }) {
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />
      <main className="flex-1">
        <article className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
          <header className="mb-10 border-b border-slate-200 pb-8 dark:border-slate-800">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">{title}</h1>
            {lastUpdated ? (
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Last updated: {lastUpdated}</p>
            ) : null}
          </header>
          <div className="space-y-8 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{children}</div>
        </article>
      </main>
      <Footer />
    </div>
  )
}

export function LegalH2({ children }) {
  return (
    <h2 className="text-base font-semibold uppercase tracking-wide text-cyan-700 dark:text-cyan-400">
      {children}
    </h2>
  )
}

export function LegalP({ children, className = '' }) {
  return <p className={className}>{children}</p>
}

export function LegalUl({ children }) {
  return <ul className="list-disc space-y-2 pl-5">{children}</ul>
}
