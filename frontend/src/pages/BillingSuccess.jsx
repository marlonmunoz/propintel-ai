import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { useAuth } from '../context/AuthContext'

export default function BillingSuccess() {
  const [searchParams] = useSearchParams()
  const { session, loading, refreshProfile, refreshQuota } = useAuth()
  const [refreshError, setRefreshError] = useState(null)
  const sessionId = searchParams.get('session_id')

  useEffect(() => {
    if (loading || !session) {
      return
    }
    void (async () => {
      try {
        await refreshProfile()
        await refreshQuota()
      } catch (e) {
        setRefreshError(e instanceof Error ? e.message : 'Could not refresh your account.')
      }
    })()
  }, [loading, session, refreshProfile, refreshQuota])

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />
      <div className="mx-auto w-full max-w-lg flex-1 px-6 pb-24 pt-24">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">You&apos;re all set</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Thanks for subscribing to PropIntel AI Pro. We&apos;re syncing your account — this usually
          takes a few seconds.
        </p>
        {!loading && !session && (
          <p className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-200">
            You&apos;re not signed in on this browser. If you just subscribed, sign in and open
            Profile — your plan should update within a few seconds after Stripe notifies us.
          </p>
        )}
        {!sessionId && session && (
          <p className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-200">
            No session id in this URL — if you just completed checkout, open Profile in a moment;
            Stripe may still be notifying our servers.
          </p>
        )}
        {refreshError && (
          <p className="mt-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
            {refreshError}
          </p>
        )}
        <Link
          to="/profile"
          className="mt-8 inline-flex rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
        >
          Back to profile
        </Link>
      </div>
      <Footer />
    </div>
  )
}
