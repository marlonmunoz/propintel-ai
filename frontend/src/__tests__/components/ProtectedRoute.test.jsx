import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProtectedRoute from '../../components/ProtectedRoute'

// Mock AuthContext so we control session/loading without touching Supabase.
vi.mock('../../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '../../context/AuthContext'

function renderRoute(sessionValue, loading = false) {
  useAuth.mockReturnValue({ session: sessionValue, loading })

  return render(
    <MemoryRouter initialEntries={['/protected']}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <div>Protected content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  it('shows loading spinner while auth is being determined', () => {
    const { container } = renderRoute(null, true)
    // The spinner is a div with animate-spin — no text content.
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })

  it('redirects to /login when there is no session', () => {
    renderRoute(null, false)
    expect(screen.getByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })

  it('renders children when a session exists', () => {
    renderRoute({ user: { id: 'u1' } }, false)
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })
})
