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

// Non-credential stubs (patterns like "password123" trigger secret scanners).
const STUB_PW_A = 'stub-reg-field-a-8chars-min-9f2a'
const STUB_PW_B = 'stub-reg-field-b-8chars-min-3d6e'
const STUB_PW_MATCH = 'stub-reg-match-8chars-minimum-ok'

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

async function agreeToLegalTerms(user) {
  await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms of Service/i }))
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
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), STUB_PW_A)
    await user.type(screen.getByPlaceholderText('••••••••'), STUB_PW_B)
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

  it('shows error when legal terms are not accepted', async () => {
    renderRegister()
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('you@example.com'), 'new@test.com')
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), STUB_PW_MATCH)
    await user.type(screen.getByPlaceholderText('••••••••'), STUB_PW_MATCH)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() =>
      expect(
        screen.getByText(/Please agree to the Terms, Privacy Policy, and disclaimer/i)
      ).toBeInTheDocument()
    )
    expect(mockSignUp).not.toHaveBeenCalled()
  })

  it('shows success screen after successful sign-up', async () => {
    mockSignUp.mockResolvedValueOnce({ error: null })
    renderRegister()
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('you@example.com'), 'new@test.com')
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), STUB_PW_MATCH)
    await user.type(screen.getByPlaceholderText('••••••••'), STUB_PW_MATCH)
    await agreeToLegalTerms(user)
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
    await user.type(screen.getByPlaceholderText('Min. 8 characters'), STUB_PW_MATCH)
    await user.type(screen.getByPlaceholderText('••••••••'), STUB_PW_MATCH)
    await agreeToLegalTerms(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() =>
      expect(screen.getByText(/Email already registered/i)).toBeInTheDocument()
    )
  })
})
