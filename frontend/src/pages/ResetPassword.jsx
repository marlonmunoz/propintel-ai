import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useTheme } from '../context/ThemeContext'
import { Moon, Sun } from 'lucide-react'
import Footer from '../components/Footer'
import PasswordInput from '../components/PasswordInput'

/**
 * Handles Supabase password recovery: user arrives with hash type=recovery or PASSWORD_RECOVERY event.
 */
export default function ResetPassword() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const [recoveryReady, setRecoveryReady] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const hash = typeof window !== 'undefined' ? window.location.hash.slice(1) : ''
    const params = new URLSearchParams(hash)
    if (params.get('type') === 'recovery') {
      setRecoveryReady(true)
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setRecoveryReady(true)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)
    try {
      const { error: updateError } = await supabase.auth.updateUser({ password })
      if (updateError) throw updateError
      await supabase.auth.signOut()
      navigate('/login', {
        replace: true,
        state: { flash: 'Your password was updated. Sign in with your new password.' },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update password.')
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
            <h1 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">Choose a new password</h1>
            {!recoveryReady ? (
              <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
                This link is invalid or expired. Request a new reset email from the sign-in page.
              </p>
            ) : (
              <>
                <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
                  Enter a new password for your account.
                </p>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {error ? (
                    <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
                      {error}
                    </div>
                  ) : null}
                  <PasswordInput
                    id="reset-password-new"
                    label="New password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    placeholder="Min. 8 characters"
                    required
                  />
                  <PasswordInput
                    id="reset-password-confirm"
                    label="Confirm new password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    autoComplete="new-password"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading ? 'Saving…' : 'Update password'}
                  </button>
                </form>
              </>
            )}

            <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
              <Link to="/login" className="font-medium text-cyan-500 hover:text-cyan-400 dark:text-cyan-400">
                Back to sign in
              </Link>
              {' · '}
              <Link
                to="/forgot-password"
                className="font-medium text-cyan-500 hover:text-cyan-400 dark:text-cyan-400"
              >
                Request new link
              </Link>
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}
