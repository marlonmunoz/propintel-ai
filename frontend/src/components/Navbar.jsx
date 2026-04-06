import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, Moon, Sun, User } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const { user, profile, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  // Login and Register pages render their own full-screen layout — hide Navbar there.
  const hideOn = ['/login', '/register']
  if (hideOn.includes(location.pathname)) return null

  const displayName =
    profile?.display_name?.trim() ||
    user?.user_metadata?.display_name ||
    user?.user_metadata?.full_name ||
    null
  const primaryLabel = displayName || user?.email?.split('@')[0] || 'Account'

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const navLink = (to, label) => (
    <Link
      to={to}
      className={`text-sm font-medium transition ${
        location.pathname === to
          ? 'text-slate-900 dark:text-white'
          : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
      }`}
    >
      {label}
    </Link>
  )

  async function handleSignOut() {
    setMenuOpen(false)
    await signOut()
    navigate('/login', { replace: true })
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500">
            <span className="text-sm font-black text-slate-950">P</span>
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
            PropIntel <span className="text-cyan-500">AI</span>
          </span>
        </Link>

        <nav className="flex items-center gap-6">
          {navLink('/', 'Home')}

          {user && (
            <>
              {navLink('/analyze', 'Analyze')}
              {navLink('/portfolio', 'Portfolio')}
            </>
          )}

          <a
            href={`${import.meta.env.VITE_API_BASE_URL}/docs`}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
          >
            API Docs
          </a>

          <button
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
      </div>
    </header>
  )
}
