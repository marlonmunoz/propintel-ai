export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="mt-auto border-t border-slate-200 bg-slate-50/90 dark:border-slate-800 dark:bg-gradient-to-t dark:from-slate-900/80 dark:to-slate-950">
      <div className="mx-auto max-w-6xl px-4 py-8 text-center sm:px-6">
        <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-500">
          © {year} PropIntel AI. Estimates are for education and decision support only — not
          financial, legal, or investment advice.
        </p>
      </div>
    </footer>
  )
}
