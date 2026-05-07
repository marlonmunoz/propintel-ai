import { LifeBuoy, Briefcase } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import SupportLink from '../components/SupportLink'

const PARTNERSHIPS_EMAIL = 'marlon@propintel-ai.com'

function partnershipsHref(subject) {
  return `mailto:${PARTNERSHIPS_EMAIL}?subject=${encodeURIComponent(subject)}`
}

export default function Contact() {
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <main className="flex-1">
        <section className="mx-auto max-w-3xl px-4 pb-16 pt-24 sm:px-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-cyan-500">
            Contact
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
            How can we help?
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            We respond to most messages within one business day. Pick the right inbox below so we can
            route your message faster.
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {/* Customer support */}
            <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-500/15">
                  <LifeBuoy className="h-5 w-5 text-cyan-600 dark:text-cyan-400" aria-hidden />
                </div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  Customer support
                </h2>
              </div>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
                For account help, password issues, billing questions, bug reports, or anything that
                isn&rsquo;t working as expected.
              </p>
              <div className="mt-5">
                <SupportLink
                  subject="PropIntel AI support request"
                  className="inline-flex w-full items-center justify-center rounded-xl bg-cyan-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cyan-500"
                >
                  Email support@propintel-ai.com
                </SupportLink>
              </div>
            </article>

            {/* Press / partnerships / investors */}
            <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15">
                  <Briefcase className="h-5 w-5 text-violet-600 dark:text-violet-400" aria-hidden />
                </div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  Press, partnerships &amp; investors
                </h2>
              </div>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
                For media inquiries, partnership opportunities, or investor outreach, reach the
                founder directly.
              </p>
              <div className="mt-5">
                <a
                  href={partnershipsHref('Partnership / press inquiry')}
                  className="inline-flex w-full items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
                >
                  Email {PARTNERSHIPS_EMAIL}
                </a>
              </div>
            </article>
          </div>

          <p className="mt-10 text-xs text-slate-500 dark:text-slate-500">
            PropIntel AI LLC — based in New York. We aim to reply within one business day.
          </p>
        </section>
      </main>

      <Footer />
    </div>
  )
}
