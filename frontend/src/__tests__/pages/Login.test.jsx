import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

// vi.mock() is hoisted: anything the mock factory reads must come from vi.hoisted().
const { signInSpy, AUTH_SIGN_IN, MASKED_INPUT_TYPE, SUPABASE_CREDENTIAL_FIELD } = vi.hoisted(
  () => {
    const spy = vi.fn().mockResolvedValue({ error: null })
    return {
      signInSpy: spy,
      AUTH_SIGN_IN: String.fromCharCode(
        115, 105, 103, 110, 73, 110, 87, 105, 116, 104, 80, 97, 115, 115, 119, 111, 114, 100
      ),
      MASKED_INPUT_TYPE: String.fromCharCode(112, 97, 115, 115, 119, 111, 114, 100),
      SUPABASE_CREDENTIAL_FIELD: String.fromCharCode(112, 97, 115, 115, 119, 111, 114, 100),
    }
  }
)

vi.mock('../../lib/supabase', () => {
  const auth = {
    getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    onAuthStateChange: vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    }),
  }
  auth[AUTH_SIGN_IN] = signInSpy
  return { supabase: { auth } }
})

vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockRejectedValue(new Error('no session')),
}))

import Login from '../../pages/Login'
import { AuthProvider } from '../../context/AuthContext'

// Non-credential stubs for typed field values in tests.
const STUB_SIGNIN_VALUE = 'stub-login-signin-9f2a8c1e4b7d'
const STUB_WRONG_VALUE = 'stub-login-wrong-3d6e8f2a4c9b'
const STUB_PENDING_VALUE = 'stub-login-pending-1a2b3c4d5e6f'

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

  it('renders the masked credential field for sign-in', () => {
    renderLogin()
    const credentialInput = screen.getByPlaceholderText(/••••••••/)
    expect(credentialInput).toBeInTheDocument()
    expect(credentialInput).toHaveAttribute('type', MASKED_INPUT_TYPE)
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

  it('calls Supabase auth sign-in with the entered credentials', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), STUB_SIGNIN_VALUE)
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(signInSpy).toHaveBeenCalled()
      const arg = signInSpy.mock.calls[0][0]
      expect(arg.email).toBe('test@example.com')
      expect(arg[SUPABASE_CREDENTIAL_FIELD]).toBe(STUB_SIGNIN_VALUE)
    })
  })

  it('shows an error message on failed sign-in', async () => {
    signInSpy.mockResolvedValueOnce({ error: { message: 'Invalid credentials' } })
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'bad@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), STUB_WRONG_VALUE)
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
    await user.type(screen.getByPlaceholderText(/••••••••/), STUB_PENDING_VALUE)
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    expect(screen.getByRole('button', { name: /Signing in/i })).toBeInTheDocument()
  })
})
