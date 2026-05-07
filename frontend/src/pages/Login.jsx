import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { Moon, Sun } from 'lucide-react'
import Footer from '../components/Footer'
import PasswordInput from '../components/PasswordInput'
import SupportLink from '../components/SupportLink'

export default function Login() {
  const { session } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [flash, setFlash] = useState(null)
  const [resendBusy, setResendBusy] = useState(false)

  useEffect(() => {
    const msg = location.state?.flash
    if (!msg) return
    setFlash(msg)
    const rest = { ...(location.state ?? {}) }
    delete rest.flash
    navigate(location.pathname, {
      replace: true,
      state: Object.keys(rest).length ? rest : {},
    })
  }, [location.pathname, location.state, navigate])

  // Already logged in — redirect
  const from = location.state?.from?.pathname ?? '/analyze'
  if (session) return <Navigate to={from} replace />

  const emailNotConfirmed =
    typeof error === 'string' &&
    /email not confirmed|confirm your email|not verified/i.test(error)

  const accountLocked =
    typeof error === 'string' &&
    /(locked|disabled|suspend(ed)?|banned|too many attempts|rate limit)/i.test(error)

  async function handleResendVerification() {
    const trimmed = email.trim()
    if (!trimmed) {
      setError('Enter your email above, then tap resend verification.')
      return
    }
    setResendBusy(true)
    setError(null)
    try {
      const { error: resendError } = await supabase.auth.resend({
        type: 'signup',
        email: trimmed,
      })
      if (resendError) throw resendError
      setFlash('Verification email sent. Check your inbox (and spam).')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resend verification email.')
    } finally {
      setResendBusy(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error: authError } = await supabase.auth.signInWithPassword({ email, password })

    if (authError) {
      setError(authError.message)
    } else {
      navigate(from, { replace: true })
    }
    setLoading(false)
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        aria-label="Toggle theme"
        className="absolute right-6 top-6 z-10 flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:text-white"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <Link to="/" className="mb-8 flex items-center justify-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500">
            <span className="text-sm font-black text-slate-950">P</span>
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            PropIntel <span className="text-cyan-500">AI</span>
          </span>
        </Link>

        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h1 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">Welcome back</h1>
          <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
            Sign in to your PropIntel account
          </p>

          {flash && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-800/50 dark:bg-emerald-950/30 dark:text-emerald-200">
              {flash}
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
              {error}
              {emailNotConfirmed ? (
                <p className="mt-2">
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resendBusy}
                    className="font-semibold text-cyan-700 underline hover:text-cyan-600 disabled:opacity-50 dark:text-cyan-400"
                  >
                    {resendBusy ? 'Sending…' : 'Resend verification email'}
                  </button>
                </p>
              ) : null}
              {accountLocked ? (
                <p className="mt-2">
                  Need help getting back in? Email{' '}
                  <SupportLink
                    subject="Login issue"
                    body="Briefly describe what happened (any error messages help us a lot):"
                    className="font-semibold text-cyan-700 underline hover:text-cyan-600 dark:text-cyan-400"
                  />
                </p>
              ) : null}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
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

            <PasswordInput
              id="login-password"
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              required
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>

            <div className="text-center">
              <Link
                to="/forgot-password"
                className="text-sm font-medium text-cyan-600 hover:text-cyan-500 dark:text-cyan-400"
              >
                Forgot password?
              </Link>
            </div>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Don&apos;t have an account?{' '}
            <Link
              to="/register"
              className="font-medium text-cyan-500 hover:text-cyan-400 dark:text-cyan-400"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
      </div>

      <Footer />
    </div>
  )
}
