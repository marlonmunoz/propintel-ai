import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutDashboard, RefreshCw } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { useAuth } from '../context/AuthContext'
import { fetchAdminOverview } from '../services/adminApi'

function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900 dark:text-white">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
    </div>
  )
}

export default function AdminDashboard() {
  const navigate = useNavigate()
  const { profile } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (profile && (profile.role || '').toLowerCase() !== 'admin') {
      navigate('/analyze', { replace: true })
      return
    }
    let cancelled = false
    setLoading(true)
    setError('')
    fetchAdminOverview()
      .then((json) => {
        if (!cancelled) setData(json)
      })
      .catch((e) => {
        if (cancelled) return
        if (e.code === 'FORBIDDEN_ADMIN') {
          navigate('/analyze', { replace: true })
          return
        }
        setError(e.message || 'Could not load admin overview.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [profile, navigate])

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400">
              <LayoutDashboard className="h-6 w-6" />
              <span className="text-sm font-semibold uppercase tracking-wide">Internal</span>
            </div>
            <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">Admin overview</h1>
            <p className="mt-1 max-w-xl text-sm text-slate-600 dark:text-slate-400">
              High-level counts and LLM usage from your database. OpenAI billing and org limits remain your primary cost controls.
            </p>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              setLoading(true)
              setError('')
              fetchAdminOverview()
                .then(setData)
                .catch((e) => {
                  if (e.code === 'FORBIDDEN_ADMIN') {
                    navigate('/analyze', { replace: true })
                    return
                  }
                  setError(e.message || 'Refresh failed.')
                })
                .finally(() => setLoading(false))
            }}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 shadow-sm transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error ? (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        {loading && !data ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading…</p>
        ) : data ? (
          <>
            <div className="mb-2 text-xs text-slate-500 dark:text-slate-400">As of {data.as_of}</div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Profiles" value={data.profiles_count} />
              <StatCard label="Saved properties" value={data.properties_count} />
              <StatCard
                label="LLM calls today"
                value={data.llm?.today_total_calls ?? '—'}
                hint={`${data.llm?.today_users_with_calls ?? 0} users with ≥1 call`}
              />
              <StatCard
                label="Quota (env defaults)"
                value={`${data.llm?.quota_free_per_day ?? '—'} / ${data.llm?.quota_paid_per_day ?? '—'}`}
                hint="Free vs paid per day"
              />
            </div>

            <div className="mt-10 grid gap-8 lg:grid-cols-2">
              <div>
                <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">LLM calls — last 7 days</h2>
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                      <tr>
                        <th className="px-4 py-2">Date</th>
                        <th className="px-4 py-2 text-right">Calls</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.llm?.last_7_days_by_date || []).length === 0 ? (
                        <tr>
                          <td colSpan={2} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                            No usage rows in range
                          </td>
                        </tr>
                      ) : (
                        data.llm.last_7_days_by_date.map((row) => (
                          <tr
                            key={row.period_date}
                            className="border-b border-slate-100 last:border-0 dark:border-slate-800/80"
                          >
                            <td className="px-4 py-2.5 font-mono text-slate-800 dark:text-slate-200">{row.period_date}</td>
                            <td className="px-4 py-2.5 text-right tabular-nums text-slate-900 dark:text-white">
                              {row.total_calls}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Top users — last 7 days</h2>
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                      <tr>
                        <th className="px-4 py-2">User</th>
                        <th className="px-4 py-2 text-right">Calls</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.llm?.top_users_last_7_days || []).length === 0 ? (
                        <tr>
                          <td colSpan={2} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                            No usage in range
                          </td>
                        </tr>
                      ) : (
                        data.llm.top_users_last_7_days.map((row) => (
                          <tr
                            key={row.user_id}
                            className="border-b border-slate-100 last:border-0 dark:border-slate-800/80"
                          >
                            <td className="max-w-[200px] truncate px-4 py-2.5 font-mono text-xs text-slate-800 dark:text-slate-200">
                              {row.user_id}
                            </td>
                            <td className="px-4 py-2.5 text-right tabular-nums text-slate-900 dark:text-white">
                              {row.calls_last_7d}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </main>
      <Footer />
    </div>
  )
}
