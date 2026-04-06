import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// jsdom doesn't ship a complete localStorage implementation in all Vitest
// configurations. Provide a simple in-memory polyfill so ThemeContext and any
// component that reads/writes localStorage works in tests.
const buildLocalStorage = () => {
  let store = {}
  return {
    getItem: (key) => Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} },
    key: (i) => Object.keys(store)[i] ?? null,
    get length() { return Object.keys(store).length },
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  value: buildLocalStorage(),
  writable: true,
})

// jsdom doesn't implement IntersectionObserver. Provide a no-op stub so
// scroll-triggered animation hooks (useInViewOnce) don't throw.
globalThis.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

// jsdom doesn't implement window.matchMedia. Provide a minimal stub so hooks
// that query media features (e.g. prefers-reduced-motion) don't throw.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})
