import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, useTheme } from '../../context/ThemeContext'

// Helper component that exposes the context values.
function ThemeConsumer() {
  const { theme, toggleTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={toggleTheme}>toggle</button>
    </div>
  )
}

function renderWithProvider() {
  return render(
    <ThemeProvider>
      <ThemeConsumer />
    </ThemeProvider>
  )
}

beforeEach(() => {
  // localStorage is cleared globally in tests/setup.js afterEach;
  // ensure the class state is also clean before each test.
  document.documentElement.classList.remove('dark')
})

describe('ThemeContext', () => {
  it('defaults to "dark" when localStorage is empty', () => {
    renderWithProvider()
    expect(screen.getByTestId('theme').textContent).toBe('dark')
  })

  it('reads saved theme from localStorage', () => {
    localStorage.setItem('theme', 'light')
    renderWithProvider()
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })

  it('adds "dark" class to <html> in dark mode', () => {
    renderWithProvider()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('removes "dark" class in light mode', () => {
    localStorage.setItem('theme', 'light')
    renderWithProvider()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('toggles from dark to light on button click', async () => {
    const user = userEvent.setup()
    renderWithProvider()
    expect(screen.getByTestId('theme').textContent).toBe('dark')
    await user.click(screen.getByRole('button', { name: /toggle/i }))
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })

  it('persists toggled theme to localStorage', async () => {
    const user = userEvent.setup()
    renderWithProvider()
    await user.click(screen.getByRole('button', { name: /toggle/i }))
    expect(localStorage.getItem('theme')).toBe('light')
  })

  it('throws when useTheme is used outside ThemeProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ThemeConsumer />)).toThrow(
      'useTheme must be used inside ThemeProvider'
    )
    spy.mockRestore()
  })
})
