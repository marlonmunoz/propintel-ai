import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, Menu, Moon, Sun, User, X } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const { user, profile, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const menuRef = useRef(null)

  // Close mobile sheet when the route changes (browser back/forward or any navigation).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional UI reset on pathname change
    setMobileNavOpen(false)
  }, [location.pathname])

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
      if (mobileNavOpen && !e.target.closest('[data-mobile-nav]')) {
        setMobileNavOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [mobileNavOpen])

  // Login and Register pages render their own full-screen layout — hide Navbar there.
  const hideOn = ['/login', '/register']
  if (hideOn.includes(location.pathname)) return null

  const displayName =
    profile?.display_name?.trim() ||
    user?.user_metadata?.display_name ||
    user?.user_metadata?.full_name ||
    null
  const primaryLabel = displayName || user?.email?.split('@')[0] || 'Account'

  const navLinkClass = (to) =>
    `block rounded-lg px-3 py-2.5 text-sm font-medium transition md:inline-block md:rounded-none md:px-0 md:py-0 md:hover:bg-transparent ${
      location.pathname === to
        ? 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-white md:bg-transparent dark:md:bg-transparent md:font-semibold md:text-cyan-600 dark:md:text-cyan-400'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:hover:text-white md:text-slate-500 md:hover:bg-transparent dark:md:hover:bg-transparent md:hover:text-slate-900 dark:md:text-slate-400 dark:md:hover:text-white'
    }`

  const navLink = (to, label) => (
    <Link to={to} className={navLinkClass(to)} onClick={() => setMobileNavOpen(false)}>
      {label}
    </Link>
  )

  async function handleSignOut() {
    setMenuOpen(false)
    setMobileNavOpen(false)
    await signOut()
    navigate('/login', { replace: true })
  }

  const apiDocsHref = `${import.meta.env.VITE_API_BASE_URL}/docs`

  return (
    <header className="relative z-50 border-b border-slate-200 bg-white/80 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="flex min-w-0 items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-500">
            <span className="text-sm font-black text-slate-950">P</span>
          </div>
          <span className="truncate text-lg font-bold tracking-tight text-slate-900 dark:text-white">
            PropIntel <span className="text-cyan-500">AI</span>
          </span>
        </Link>

        {/* Desktop / tablet — horizontal nav */}
        <nav className="hidden items-center gap-6 md:flex">
          {navLink('/', 'Home')}

          {user && (
            <>
              {navLink('/analyze', 'Analyze')}
              {navLink('/portfolio', 'Portfolio')}
            </>
          )}

          <a
            href={apiDocsHref}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
          >
            API Docs
          </a>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-white"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {user ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="flex max-w-[220px] items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-left transition hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
                aria-expanded={menuOpen}
                aria-haspopup="true"
              >
                <User className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-800 dark:text-slate-200">
                  {primaryLabel}
                </span>
                {(profile?.role || '').toLowerCase() === 'admin' && (
                  <span className="shrink-0 rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-800 dark:bg-violet-900/50 dark:text-violet-200">
                    Admin
                  </span>
                )}
                <ChevronDown
                  className={`h-4 w-4 shrink-0 text-slate-400 transition ${menuOpen ? 'rotate-180' : ''}`}
                />
              </button>

              {menuOpen && (
                <div className="absolute right-0 z-50 mt-1 w-56 rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                  <div className="border-b border-slate-100 px-3 py-2 dark:border-slate-800">
                    {displayName && (
                      <div className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                        {displayName}
                      </div>
                    )}
                    <div className="truncate text-xs text-slate-500 dark:text-slate-400">{user.email}</div>
                    {(profile?.role || '').toLowerCase() === 'admin' && (
                      <div className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">
                        Admin — full portfolio access
                      </div>
                    )}
                  </div>
                  <Link
                    to="/profile"
                    className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
                    onClick={() => setMenuOpen(false)}
                  >
                    Profile settings
                  </Link>
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="text-sm font-medium text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-cyan-500 px-3.5 py-1.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                Get started
              </Link>
            </div>
          )}
        </nav>

        {/* Mobile — compact controls; full menu opens in panel below */}
        <div
          className="flex items-center gap-2 md:hidden"
          data-mobile-nav
        >
          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-white"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={() => setMobileNavOpen((o) => !o)}
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-nav-panel"
            aria-label={mobileNavOpen ? 'Close menu' : 'Open menu'}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {mobileNavOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile full-width panel (screens below md breakpoint) */}
      {mobileNavOpen && (
        <div
          id="mobile-nav-panel"
          className="border-t border-slate-200 bg-white shadow-lg dark:border-slate-800 dark:bg-slate-950 md:hidden"
          data-mobile-nav
        >
          <nav className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-4 sm:px-6">
            {navLink('/', 'Home')}
            {user && (
              <>
                {navLink('/analyze', 'Analyze')}
                {navLink('/portfolio', 'Portfolio')}
              </>
            )}
            <a
              href={apiDocsHref}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:hover:text-white"
              onClick={() => setMobileNavOpen(false)}
            >
              API Docs
            </a>

            {user ? (
              <div className="mt-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                <p className="px-3 text-xs font-medium uppercase tracking-wide text-slate-400">Account</p>
                {displayName && (
                  <p className="px-3 pt-2 text-sm font-semibold text-slate-900 dark:text-white">{displayName}</p>
                )}
                <p className="px-3 pb-2 text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
                {(profile?.role || '').toLowerCase() === 'admin' && (
                  <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">
                    Admin — full portfolio access
                  </p>
                )}
                <Link
                  to="/profile"
                  className="mt-1 block rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
                  onClick={() => setMobileNavOpen(false)}
                >
                  Profile settings
                </Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-rose-600 transition hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            ) : (
              <div className="mt-2 flex flex-col gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                <Link
                  to="/login"
                  className="rounded-lg px-3 py-2.5 text-center text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                  onClick={() => setMobileNavOpen(false)}
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="rounded-lg bg-cyan-500 py-2.5 text-center text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
                  onClick={() => setMobileNavOpen(false)}
                >
                  Get started
                </Link>
              </div>
            )}
          </nav>
        </div>
      )}
    </header>
  )
}
