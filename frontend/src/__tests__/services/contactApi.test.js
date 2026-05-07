import { describe, it, expect, vi, beforeEach } from 'vitest'
import { sendContactMessage } from '../../services/contactApi'

const BASE = 'http://localhost:8000'

const VALID_PAYLOAD = {
  name: 'Jane Smith',
  email: 'jane@example.com',
  topic: 'support',
  message: 'Hello, I need help with my account.',
}

describe('contactApi — sendContactMessage()', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('POSTs to /contact with the correct body', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, message: "Message sent. We'll get back to you soon." }),
    })

    const result = await sendContactMessage(VALID_PAYLOAD)

    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe(`${BASE}/contact`)
    expect(options.method).toBe('POST')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(options.body)).toEqual(VALID_PAYLOAD)
    expect(result.ok).toBe(true)
  })

  it('throws with the server detail on a 422 validation error', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Message must be at least 10 characters.' }),
    })

    await expect(sendContactMessage({ ...VALID_PAYLOAD, message: 'short' })).rejects.toThrow(
      'Message must be at least 10 characters.'
    )
  })

  it('throws with the server message field when detail is missing', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ message: 'Email service is temporarily unavailable.' }),
    })

    await expect(sendContactMessage(VALID_PAYLOAD)).rejects.toThrow(
      'Email service is temporarily unavailable.'
    )
  })

  it('throws a generic fallback when no parseable error body', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => { throw new SyntaxError('bad json') },
    })

    await expect(sendContactMessage(VALID_PAYLOAD)).rejects.toThrow(
      'Failed to send message. Please try again or email us directly.'
    )
  })
})
