import { useState } from 'react'
import { Link } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useTheme } from '../context/ThemeContext'
import { Moon, Sun } from 'lucide-react'
import Footer from '../components/Footer'

/** Must match an entry in Supabase Dashboard → Authentication → URL Configuration → Redirect URLs. */
function resetRedirectUrl() {
  const base = import.meta.env.VITE_SITE_URL?.replace(/\/$/, '') || window.location.origin
  return `${base}/reset-password`
}

export default function ForgotPassword() {
  const { theme, toggleTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sent, setSent] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: resetRedirectUrl(),
      })
      if (resetError) throw resetError
      setSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      <button
        onClick={toggleTheme}
        aria-label="Toggle theme"
        className="absolute right-6 top-6 z-10 flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:text-white"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-8 flex items-center justify-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500">
              <span className="text-sm font-black text-slate-950">P</span>
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              PropIntel <span className="text-cyan-500">AI</span>
            </span>
          </Link>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h1 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">Reset password</h1>
            <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
              Enter your account email and we&apos;ll send you a link to choose a new password.
            </p>

            {sent ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-800/50 dark:bg-emerald-950/30 dark:text-emerald-200">
                If an account exists for <strong>{email.trim()}</strong>, you&apos;ll receive an email
                shortly. Check spam if you don&apos;t see it.
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {error ? (
                  <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
                    {error}
                  </div>
                ) : null}
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Email
                  </label>
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 transition focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
            )}

            <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
              <Link to="/login" className="font-medium text-cyan-500 hover:text-cyan-400 dark:text-cyan-400">
                Back to sign in
              </Link>
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}
