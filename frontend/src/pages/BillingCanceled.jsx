import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function BillingCanceled() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />
      <div className="mx-auto w-full max-w-lg flex-1 px-6 pb-24 pt-24">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Checkout canceled</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          No charges were made. You can upgrade anytime from your profile when you&apos;re ready.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/profile"
            className="inline-flex rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
          >
            Back to profile
          </Link>
          <Link
            to="/analyze"
            className="inline-flex rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Continue analyzing
          </Link>
        </div>
      </div>
      <Footer />
    </div>
  )
}
