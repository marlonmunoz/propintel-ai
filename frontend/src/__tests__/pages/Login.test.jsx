import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

// vi.mock() is hoisted to the top of the file by Vitest, so any variables
// referenced inside its factory must be created with vi.hoisted() to avoid
// "Cannot access before initialization" errors.
const mockSignIn = vi.hoisted(() => vi.fn().mockResolvedValue({ error: null }))

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signInWithPassword: mockSignIn,
    },
  },
}))

vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockRejectedValue(new Error('no session')),
}))

import Login from '../../pages/Login'
import { AuthProvider } from '../../context/AuthContext'

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
    await user.type(screen.getByPlaceholderText(/••••••••/), 'mypassword')
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() =>
      expect(mockSignIn).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'mypassword',
      })
    )
  })

  it('shows an error message on failed sign-in', async () => {
    mockSignIn.mockResolvedValueOnce({ error: { message: 'Invalid credentials' } })
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'bad@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() =>
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    )
  })

  it('shows "Signing in…" while the request is pending', async () => {
    mockSignIn.mockImplementationOnce(() => new Promise(() => {})) // never resolves
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/••••••••/), 'pass')
    await user.click(screen.getByRole('button', { name: /Sign in/i }))

    expect(screen.getByRole('button', { name: /Signing in/i })).toBeInTheDocument()
  })
})
