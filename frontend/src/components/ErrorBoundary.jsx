import { Component } from 'react'
import { Link } from 'react-router-dom'

/**
 * Catches uncaught errors in the route tree and shows a recovery UI instead of a blank screen.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('[PropIntel ErrorBoundary]', error, info.componentStack)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-6 py-16 text-center dark:bg-slate-950">
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Something went wrong
          </h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            The app hit an unexpected error. You can try reloading the page or return home.
            If this keeps happening, check the browser console for details.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={this.handleReload}
              className="rounded-xl bg-cyan-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cyan-500"
            >
              Reload page
            </button>
            <Link
              to="/"
              onClick={this.handleReset}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              Back to home
            </Link>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
