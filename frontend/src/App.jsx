import { lazy, Suspense } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import PageErrorBoundary from './components/PageErrorBoundary'

// Each page is its own JS chunk — only downloaded when the user navigates to it.
const Home = lazy(() => import('./pages/Home'))
const Analyze = lazy(() => import('./pages/Analyze'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const Profile = lazy(() => import('./pages/Profile'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const TermsOfService = lazy(() => import('./pages/TermsOfService'))
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy'))
const ValuationDisclaimer = lazy(() => import('./pages/ValuationDisclaimer'))
const Contact = lazy(() => import('./pages/Contact'))
const BillingSuccess = lazy(() => import('./pages/BillingSuccess'))
const BillingCanceled = lazy(() => import('./pages/BillingCanceled'))

function PageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent" />
    </div>
  )
}

/**
 * Inner component so we can read useLocation() and pass it as the key to
 * PageErrorBoundary.  This resets the error boundary on every navigation:
 * a crash on /analyze does not block the user from going to /portfolio.
 */
function AppRoutes() {
  const location = useLocation()
  return (
    <PageErrorBoundary key={location.pathname}>
      <Suspense fallback={<PageSpinner />}>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/disclaimer" element={<ValuationDisclaimer />} />
          <Route path="/contact" element={<Contact />} />

          {/* Protected — requires a valid Supabase session */}
          <Route
            path="/analyze"
            element={
              <ProtectedRoute>
                <Analyze />
              </ProtectedRoute>
            }
          />
          <Route
            path="/portfolio"
            element={
              <ProtectedRoute>
                <Portfolio />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          {/* Billing return URLs — public so Stripe redirects always render (session is
              per-origin; refreshProfile/refreshQuota no-op when logged out). */}
          <Route path="/billing/success" element={<BillingSuccess />} />
          <Route path="/billing/canceled" element={<BillingCanceled />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Suspense>
    </PageErrorBoundary>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
