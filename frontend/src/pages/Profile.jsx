import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Zap, ShieldCheck, Crown, Lock } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import PasswordInput from '../components/PasswordInput'
import SupportLink from '../components/SupportLink'
import { useAuth } from '../context/AuthContext'
import {
  updateProfile,
  changePassword,
  requestPasswordReauthNonce,
  isPasswordChangeReauthRequired,
} from '../services/authApi'

const TIER_CONFIG = {
  admin: {
    label: 'Admin',
    description: 'Full access — unlimited AI analyses and portfolio visibility for all users.',
    pillClass: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200',
    Icon: ShieldCheck,
    iconClass: 'text-violet-500',
  },
  paid: {
    label: 'Paid',
    description: 'Up to 200 AI-powered investment analyses per day.',
    pillClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
    Icon: Crown,
    iconClass: 'text-emerald-500',
  },
  user: {
    label: 'Free',
    description: 'Up to 10 AI-powered investment analyses per day.',
    pillClass: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    Icon: Zap,
    iconClass: 'text-slate-400',
  },
}

function QuotaBar({ quota }) {
  if (!quota) return null

  const { daily_limit, used_today, remaining, resets_at } = quota
  const isUnlimited = daily_limit === null

  if (isUnlimited) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
          Daily AI Analyses
        </p>
        <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Unlimited</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          No daily cap on AI explanation calls.
        </p>
      </div>
    )
  }

  const pct = daily_limit > 0 ? Math.min(100, Math.round((used_today / daily_limit) * 100)) : 0
  const isExhausted = remaining === 0
  const isWarning = !isExhausted && pct >= 70

  const barClass = isExhausted
    ? 'bg-rose-500'
    : isWarning
      ? 'bg-amber-400'
      : 'bg-cyan-500'

  const resetDate = resets_at
    ? new Date(resets_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : null

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-baseline justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
          Daily AI Analyses
        </p>
        {resetDate && (
          <p className="text-xs text-slate-400 dark:text-slate-500">Resets {resetDate}</p>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-2xl font-bold text-slate-900 dark:text-white">{used_today}</span>
        <span className="text-sm text-slate-400 dark:text-slate-500">/ {daily_limit} used today</span>
      </div>

      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barClass}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={used_today}
          aria-valuemin={0}
          aria-valuemax={daily_limit}
          aria-label="Daily AI analyses used"
        />
      </div>

      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
        {isExhausted
          ? 'Quota reached for today. Resets at midnight UTC.'
          : `${remaining} remaining today`}
      </p>
    </div>
  )
}

function UpgradeCta() {
  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 dark:border-emerald-800/50 dark:bg-emerald-950/20">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15">
          <Crown className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-900 dark:text-white">Upgrade to Paid</p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Get 200 AI analyses per day — 20× more than the free tier. Ideal for active investors
            analyzing multiple properties daily.
          </p>
          <ul className="mt-3 space-y-1 text-sm text-slate-600 dark:text-slate-400">
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
              200 AI-powered analyses per day
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
              Same fast ML valuation engine
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
              Priority support
            </li>
          </ul>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled
              title="Stripe checkout — coming soon"
              className="inline-flex cursor-not-allowed items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white opacity-60 transition"
              aria-label="Upgrade to Paid — payment integration coming soon"
            >
              <Crown className="h-4 w-4" />
              Upgrade — coming soon
            </button>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Stripe payment integration in progress
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Profile() {
  const { profile, quota, refreshProfile, user } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [marketingOptIn, setMarketingOptIn] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [reauthNonce, setReauthNonce] = useState('')
  const [pwAwaitingNonce, setPwAwaitingNonce] = useState(false)
  const [pwSubmitting, setPwSubmitting] = useState(false)
  const [pwError, setPwError] = useState(null)
  const [pwSuccess, setPwSuccess] = useState(null)

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

  function resetPasswordFieldsOnly() {
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setReauthNonce('')
    setPwAwaitingNonce(false)
  }

  function cancelPasswordChange() {
    resetPasswordFieldsOnly()
    setPwError(null)
    setPwSuccess(null)
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault()
    setPwError(null)
    setPwSuccess(null)

    if (newPassword !== confirmPassword) {
      setPwError('New passwords do not match.')
      return
    }
    if (newPassword.length < 8) {
      setPwError('New password must be at least 8 characters.')
      return
    }
    if (newPassword === currentPassword) {
      setPwError('New password must be different from your current password.')
      return
    }

    setPwSubmitting(true)
    try {
      if (pwAwaitingNonce) {
        const code = reauthNonce.trim()
        if (!code) {
          setPwError('Enter the verification code from your email.')
          setPwSubmitting(false)
          return
        }
        await changePassword({
          currentPassword,
          newPassword,
          nonce: code,
        })
        setPwError(null)
        setPwSuccess('Password updated.')
        resetPasswordFieldsOnly()
      } else {
        await changePassword({ currentPassword, newPassword })
        setPwError(null)
        setPwSuccess('Password updated.')
        resetPasswordFieldsOnly()
      }
    } catch (err) {
      if (!pwAwaitingNonce && isPasswordChangeReauthRequired(err)) {
        try {
          await requestPasswordReauthNonce()
          setPwAwaitingNonce(true)
          setPwError(null)
          setPwSuccess(
            `We sent a verification code to ${user?.email ?? 'your email'}. Enter it below to finish.`
          )
        } catch (sendErr) {
          setPwError(sendErr instanceof Error ? sendErr.message : 'Could not send verification code.')
        }
      } else {
        setPwError(err instanceof Error ? err.message : 'Password update failed.')
      }
    } finally {
      setPwSubmitting(false)
    }
  }

  async function handleResendReauthCode() {
    setPwError(null)
    setPwSuccess(null)
    setPwSubmitting(true)
    try {
      await requestPasswordReauthNonce()
      setPwSuccess(`A new code was sent to ${user?.email ?? 'your email'}.`)
    } catch (err) {
      setPwError(err instanceof Error ? err.message : 'Could not resend code.')
    } finally {
      setPwSubmitting(false)
    }
  }

  const role = (profile?.role || 'user').toLowerCase()
  const tier = TIER_CONFIG[role] ?? TIER_CONFIG.user
  const { Icon } = tier
  const isFree = role === 'user'

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <div className="mx-auto w-full max-w-lg px-6 pb-24 pt-24">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-cyan-500">Account</p>
        <h1 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">Profile</h1>
        <p className="mb-8 text-sm text-slate-500 dark:text-slate-400">
          Manage your account settings and view your AI analysis usage.
        </p>

        <div className="space-y-4">
          {/* ── Tier card ─────────────────────────────────────────────────── */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
              Current Plan
            </p>
            <div className="mt-3 flex items-center gap-3">
              <Icon className={`h-6 w-6 shrink-0 ${tier.iconClass}`} aria-hidden />
              <span className={`rounded-full px-3 py-1 text-sm font-bold ${tier.pillClass}`}>
                {tier.label}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{tier.description}</p>
          </div>

          {/* ── Quota usage bar ───────────────────────────────────────────── */}
          <QuotaBar quota={quota} />

          {/* ── Upgrade CTA (free users only) ─────────────────────────────── */}
          {isFree && <UpgradeCta />}

          {/* ── Profile edit form ─────────────────────────────────────────── */}
          <form
            onSubmit={handleSubmit}
            className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
              Account Details
            </p>
            <div className="mb-4 text-xs text-slate-500 dark:text-slate-400">
              Signed in as{' '}
              <span className="font-medium text-slate-700 dark:text-slate-300">{user?.email}</span>
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

          {/* ── Change password (Supabase: current password + optional reauth nonce) ── */}
          <form
            onSubmit={handlePasswordSubmit}
            className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="mb-4 flex items-center gap-2">
              <Lock className="h-5 w-5 text-slate-400" aria-hidden />
              <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                Change password
              </h2>
            </div>
            <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
              Uses your Supabase email provider settings (require current password, secure password
              change). If your session is older than 24 hours, we will email you a one-time code to
              complete the update.
            </p>

            {pwError && (
              <div className="mb-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
                {pwError}
              </div>
            )}
            {pwSuccess && (
              <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300">
                {pwSuccess}
              </div>
            )}

            <div className="space-y-4">
              <PasswordInput
                id="profile-current-password"
                label="Current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
              />
              <PasswordInput
                id="profile-new-password"
                label="New password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                placeholder="Min. 8 characters"
              />
              <PasswordInput
                id="profile-confirm-password"
                label="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                placeholder="••••••••"
              />

              {pwAwaitingNonce && (
                <div>
                  <label
                    htmlFor="profile-reauth-nonce"
                    className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
                  >
                    Email verification code
                  </label>
                  <input
                    id="profile-reauth-nonce"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={reauthNonce}
                    onChange={(e) => setReauthNonce(e.target.value)}
                    placeholder="Enter code from email"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  />
                  <button
                    type="button"
                    onClick={handleResendReauthCode}
                    disabled={pwSubmitting}
                    className="mt-2 text-sm font-medium text-cyan-600 hover:text-cyan-500 disabled:opacity-50 dark:text-cyan-400"
                  >
                    Resend code
                  </button>
                </div>
              )}
            </div>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                type="submit"
                disabled={pwSubmitting}
                className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                {pwSubmitting
                  ? 'Updating…'
                  : pwAwaitingNonce
                    ? 'Complete password update'
                    : 'Update password'}
              </button>
              {(pwAwaitingNonce || currentPassword || newPassword || confirmPassword || reauthNonce) && (
                <button
                  type="button"
                  onClick={cancelPasswordChange}
                  disabled={pwSubmitting}
                  className="text-sm font-medium text-slate-500 hover:text-slate-700 disabled:opacity-50 dark:text-slate-400 dark:hover:text-slate-200"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>

          {/* ── Close account (Supabase delete requires admin API — support-led for now) ── */}
          <div className="rounded-2xl border border-rose-200/80 bg-rose-50/50 p-6 dark:border-rose-900/40 dark:bg-rose-950/20">
            <p className="text-xs font-semibold uppercase tracking-widest text-rose-700 dark:text-rose-400">
              Close account
            </p>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              To delete your PropIntel account and associated saved analyses, email{' '}
              <SupportLink subject="Account deletion request" /> from your registered address. We will
              confirm identity and process deletion within a reasonable time, subject to legal
              retention needs.
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}
