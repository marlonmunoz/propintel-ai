import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, Moon, Sun, User } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const { user, signOut } = useAuth()

  // Login and Register pages render their own full-screen layout — hide Navbar there.
  const hideOn = ['/login', '/register']
  if (hideOn.includes(location.pathname)) return null

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

          {/* Only show app links when logged in */}
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

          {/* Auth section */}
          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 dark:border-slate-700">
                <User className="h-3.5 w-3.5 text-slate-400" />
                <span className="max-w-[140px] truncate text-xs text-slate-600 dark:text-slate-400">
                  {user.email}
                </span>
              </div>
              <button
                onClick={handleSignOut}
                aria-label="Sign out"
                title="Sign out"
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:border-rose-300 hover:text-rose-600 dark:border-slate-700 dark:text-slate-400 dark:hover:border-rose-700 dark:hover:text-rose-400"
              >
                <LogOut className="h-4 w-4" />
              </button>
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
