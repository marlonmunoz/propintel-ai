import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

/* ── Mocks ────────────────────────────────────────────────────────────────── */

vi.mock('../../components/Navbar', () => ({
  default: () => <nav data-testid="navbar" />,
}))

const mockSend = vi.hoisted(() => vi.fn())
vi.mock('../../services/contactApi', () => ({
  sendContactMessage: mockSend,
}))

/* ── Helpers ──────────────────────────────────────────────────────────────── */

import Contact from '../../pages/Contact'

function renderContact() {
  return render(
    <MemoryRouter>
      <Contact />
    </MemoryRouter>
  )
}

function fillForm({ name = 'Jane Smith', email = 'jane@example.com', message = 'I need help with my account please.' } = {}) {
  fireEvent.change(screen.getByLabelText(/your name/i), { target: { value: name } })
  fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: email } })
  fireEvent.change(screen.getByLabelText(/message/i), { target: { value: message } })
}

/* ── Tests ────────────────────────────────────────────────────────────────── */

describe('Contact page', () => {
  beforeEach(() => {
    mockSend.mockReset()
  })

  it('renders the page heading', () => {
    renderContact()
    expect(screen.getByRole('heading', { name: /how can we help/i })).toBeInTheDocument()
  })

  it('renders both topic cards', () => {
    renderContact()
    expect(screen.getByRole('button', { name: /customer support/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /press, partnerships/i })).toBeInTheDocument()
  })

  it('renders the contact form with all fields', () => {
    renderContact()
    expect(screen.getByLabelText(/your name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
  })

  it('defaults to "support" topic', () => {
    renderContact()
    const radios = screen.getAllByRole('radio')
    const supportRadio = radios.find((r) => r.value === 'support')
    expect(supportRadio.checked).toBe(true)
  })

  it('clicking the partnerships card pre-selects that topic', async () => {
    renderContact()
    await userEvent.click(screen.getByRole('button', { name: /press, partnerships/i }))
    const radios = screen.getAllByRole('radio')
    const partnerRadio = radios.find((r) => r.value === 'partnerships')
    expect(partnerRadio.checked).toBe(true)
  })

  it('submits the form and shows success banner on success', async () => {
    mockSend.mockResolvedValueOnce({ ok: true, message: "Message sent. We'll get back to you soon." })
    renderContact()
    fillForm()

    await userEvent.click(screen.getByRole('button', { name: /send message/i }))

    await waitFor(() => {
      expect(screen.getByText(/message sent!/i)).toBeInTheDocument()
    })
    expect(mockSend).toHaveBeenCalledWith({
      name: 'Jane Smith',
      email: 'jane@example.com',
      topic: 'support',
      message: 'I need help with my account please.',
    })
  })

  it('shows an error banner when the API call fails', async () => {
    mockSend.mockRejectedValueOnce(new Error('Email service is temporarily unavailable.'))
    renderContact()
    fillForm()

    await userEvent.click(screen.getByRole('button', { name: /send message/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/email service is temporarily unavailable/i)
    })
  })

  it('"Send another message" link resets the form', async () => {
    mockSend.mockResolvedValueOnce({ ok: true, message: 'ok' })
    renderContact()
    fillForm()

    await userEvent.click(screen.getByRole('button', { name: /send message/i }))
    await screen.findByText(/message sent!/i)

    await userEvent.click(screen.getByRole('button', { name: /send another message/i }))
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
  })
})
