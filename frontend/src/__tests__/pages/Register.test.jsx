import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../../context/ThemeContext'

const mockSignUp = vi.hoisted(() => vi.fn())

vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signUp: mockSignUp,
    },
  },
}))

vi.mock('../../services/authApi', () => ({
  fetchProfile: vi.fn().mockRejectedValue(new Error('no session')),
  fetchQuota: vi.fn().mockResolvedValue(null),
}))

import Register from '../../pages/Register'
import { AuthProvider } from '../../context/AuthContext'

function renderRegister() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={['/register']}>
          <Register />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

describe('Register page', () => {
  it('renders the Create an account heading', () => {
    renderRegister()
    expect(screen.getByRole('heading', { name: /Create an account/i })).toBeInTheDocument()
  })

  it('renders email and password inputs by placeholder', () => {
    renderRegister()
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Min. 8 characters')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('shows error when passwords do not match', async () => {
    renderRegister()
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('you@example.com'), 'test@test.com')
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), 'password123')
    await user.type(screen.getByPlaceholderText('••••••••'), 'different123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() =>
      expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument()
    )
  })

  it('shows error when password is fewer than 8 characters', async () => {
    renderRegister()
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('you@example.com'), 'test@test.com')
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), 'short')
    await user.type(screen.getByPlaceholderText('••••••••'), 'short')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() =>
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()
    )
  })

  it('shows success screen after successful sign-up', async () => {
    mockSignUp.mockResolvedValueOnce({ error: null })
    renderRegister()
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('you@example.com'), 'new@test.com')
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), 'password123')
    await user.type(screen.getByPlaceholderText('••••••••'), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() =>
      expect(screen.getByText(/Check your email/i)).toBeInTheDocument()
    )
  })

  it('shows Supabase error message on sign-up failure', async () => {
    mockSignUp.mockResolvedValueOnce({ error: { message: 'Email already registered' } })
    renderRegister()
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('you@example.com'), 'taken@test.com')
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), 'password123')
    await user.type(screen.getByPlaceholderText('••••••••'), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() =>
      expect(screen.getByText(/Email already registered/i)).toBeInTheDocument()
    )
  })
})
