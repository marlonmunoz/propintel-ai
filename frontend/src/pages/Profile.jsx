import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { useAuth } from '../context/AuthContext'
import { updateProfile } from '../services/authApi'

export default function Profile() {
  const { profile, refreshProfile, user } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [marketingOptIn, setMarketingOptIn] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (profile) {
      setDisplayName(profile.display_name || '')
      setMarketingOptIn(profile.marketing_opt_in)
    }
  }, [profile])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      await updateProfile({
        display_name: displayName.trim() || null,
        marketing_opt_in: marketingOptIn,
      })
      await refreshProfile()
      setMessage('Saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <div className="mx-auto flex-1 max-w-lg px-6 pb-24 pt-24">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-cyan-500">Account</p>
        <h1 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">Profile</h1>
        <p className="mb-8 text-sm text-slate-500 dark:text-slate-400">
          Update how your name appears in the app. Sign-in always uses your email and password.
        </p>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="mb-4 text-xs text-slate-500 dark:text-slate-400">
            Signed in as <span className="font-medium text-slate-700 dark:text-slate-300">{user?.email}</span>
          </div>

          {error && (
            <div className="mb-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
              {error}
            </div>
          )}
          {message && (
            <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400">
              {message}
            </div>
          )}

          <div className="mb-4">
            <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Display name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <label className="mb-6 flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={marketingOptIn}
              onChange={(e) => setMarketingOptIn(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-cyan-500"
            />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              Send me occasional product updates and NYC market insights
            </span>
          </label>

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
          >
            {saving ? 'Saving…' : 'Save changes'}
          </button>

          <Link
            to="/analyze"
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
            Back to Analyze
          </Link>
        </form>
      </div>

      <Footer />
    </div>
  )
}
