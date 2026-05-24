import { Component } from 'react'
import { Link } from 'react-router-dom'

/**
 * Class-based error boundary that catches unhandled render errors in its subtree.
 *
 * Usage in App.jsx:
 *   <PageErrorBoundary key={location.pathname}>
 *     <Routes>...</Routes>
 *   </PageErrorBoundary>
 *
 * Passing `location.pathname` as the `key` makes React unmount and remount
 * the boundary on every navigation, so an error on /analyze does not block
 * the user from navigating to /portfolio or any other route.
 */
export default class PageErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, errorMessage: '' }
    this.handleReset = this.handleReset.bind(this)
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message ?? 'An unexpected error occurred.',
    }
  }

  componentDidCatch(error, info) {
    // In production, wire this to Sentry or your error tracking service.
    console.error('[PageErrorBoundary] Caught render error:', error, info)
  }

  handleReset() {
    this.setState({ hasError: false, errorMessage: '' })
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 dark:bg-rose-950/40">
            <svg
              className="h-7 w-7 text-rose-500"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
              />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
            Something went wrong
          </h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            An unexpected error occurred on this page. Your other pages and data
            are not affected.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <button
              onClick={this.handleReset}
              className="rounded-xl bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
            >
              Try again
            </button>
            <Link
              to="/"
              onClick={this.handleReset}
              className="rounded-xl border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    )
  }
}
