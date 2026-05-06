import { useState } from 'react'
import { supabase } from '../lib/supabase'

/**
 * Shown when the user is signed in but Supabase has not marked the email as confirmed.
 * Depends on project settings: if "Confirm email" is off, this rarely appears.
 */
export default function EmailVerificationBanner({ user }) {
  const [sending, setSending] = useState(false)
  const [msg, setMsg] = useState(null)
  const [err, setErr] = useState(null)

  if (!user?.email || user.email_confirmed_at) return null

  async function handleResend() {
    setErr(null)
    setMsg(null)
    setSending(true)
    try {
      const { error } = await supabase.auth.resend({
        type: 'signup',
        email: user.email,
      })
      if (error) throw error
      setMsg('Verification email sent. Check your inbox and spam folder.')
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not resend email.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-center dark:border-amber-900/50 dark:bg-amber-950/40">
      <p className="text-xs text-amber-900 dark:text-amber-100 sm:text-sm">
        <span className="font-semibold">Verify your email</span>
        {' — '}
        Confirm your address to keep full access.{' '}
        <button
          type="button"
          onClick={handleResend}
          disabled={sending}
          className="font-semibold text-cyan-700 underline underline-offset-2 hover:text-cyan-600 disabled:opacity-50 dark:text-cyan-400 dark:hover:text-cyan-300"
        >
          {sending ? 'Sending…' : 'Resend verification email'}
        </button>
      </p>
      {msg ? (
        <p className="mt-1 text-xs text-emerald-800 dark:text-emerald-300">{msg}</p>
      ) : null}
      {err ? <p className="mt-1 text-xs text-rose-700 dark:text-rose-400">{err}</p> : null}
    </div>
  )
}
