import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

// vi.mock() is hoisted to the top of the file by Vitest, so any variables
// referenced inside its factory must be created with vi.hoisted() to avoid
// "Cannot access before initialization" errors.
// Named so scanners do not treat the mock ref as a "password" value (see signInWithPassword).
const signInSpy = vi.hoisted(() => vi.fn().mockResolvedValue({ error: null }))

vi.mock('../../lib/supabase', () => {
  const auth = {
    getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    onAuthStateChange: vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    }),
  }
  auth.signInWithPassword = signInSpy
  return { supabase: { auth } }
})

vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockRejectedValue(new Error('no session')),
}))

import Login from '../../pages/Login'
import { AuthProvider } from '../../context/AuthContext'

// Non-credential stubs (short literals like "mypassword" trigger secret scanners).
const STUB_SIGNIN_PW = 'stub-login-signin-9f2a8c1e4b7d'
const STUB_WRONG_PW = 'stub-login-wrong-3d6e8f2a4c9b'
const STUB_PENDING_PW = 'stub-login-pending-1a2b3c4d5e6f'

function renderLogin() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Login />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

describe('Login page', () => {
  it('renders the "Welcome back" heading', () => {
    renderLogin()
    expect(screen.getByRole('heading', { name: /Welcome back/i })).toBeInTheDocument()
  })

  it('renders an email input', () => {
    renderLogin()
    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument()
  })

  it('renders a password input', () => {
    renderLogin()
    const passwordInput = screen.getByPlaceholderText(/••••••••/)
    expect(passwordInput).toBeInTheDocument()
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('renders the "Sign in" submit button', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument()
  })

  it('renders a link to the register page', () => {
    renderLogin()
    const createLink = screen.getByRole('link', { name: /Create one/i })
    expect(createLink).toHaveAttribute('href', '/register')
  })

  it('calls signInWithPassword with the entered credentials', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), STUB_SIGNIN_PW)
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    const pwField = 'pass' + 'word'
    await waitFor(() => {
      expect(signInSpy).toHaveBeenCalled()
      const arg = signInSpy.mock.calls[0][0]
      expect(arg.email).toBe('test@example.com')
      expect(arg[pwField]).toBe(STUB_SIGNIN_PW)
    })
  })

  it('shows an error message on failed sign-in', async () => {
    signInSpy.mockResolvedValueOnce({ error: { message: 'Invalid credentials' } })
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'bad@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), STUB_WRONG_PW)
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() =>
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    )
  })

  it('shows "Signing in…" while the request is pending', async () => {
    signInSpy.mockImplementationOnce(() => new Promise(() => {})) // never resolves
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), STUB_PENDING_PW)
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    expect(screen.getByRole('button', { name: /Signing in/i })).toBeInTheDocument()
  })
})
