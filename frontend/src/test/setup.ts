import '@testing-library/jest-dom'
import { vi } from 'vitest'

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query.includes('prefers-reduced-motion')
      ? false
      : query.includes('min-width'),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

class ResizeObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
})

class IntersectionObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: IntersectionObserverMock,
})

if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => undefined
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => undefined
}

Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => undefined)

window.scrollTo = window.scrollTo || (() => undefined)

export const mockSignInWithOAuth = vi.fn().mockResolvedValue({ data: {}, error: null })
export const mockSignOut = vi.fn().mockResolvedValue({ error: null })

export function createMockSupabaseClient() {
  return {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
      signInWithOAuth: mockSignInWithOAuth,
      signOut: mockSignOut,
    },
  }
}

export const defaultProfileResponse = {
  user_id: '00000000-0000-0000-0000-000000000001',
  display_currency: 'CAD',
  default_threshold_pct: 20,
  notifications_enabled: true,
  email_digest_enabled: true,
  theme: 'light',
  revisit_prompts_enabled: true,
  revisit_on_sale_enabled: true,
  revisit_stale_enabled: true,
  revisit_stale_days: 30,
  created_at: '2026-06-14T00:00:00.000Z',
  updated_at: '2026-06-14T00:00:00.000Z',
}

const originalFetch = globalThis.fetch.bind(globalThis)

vi.stubGlobal(
  'fetch',
  vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.includes('/api/profile')) {
      return new Response(JSON.stringify(defaultProfileResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    return originalFetch(input, init)
  }),
)

vi.mock('../lib/supabase.ts', () => ({
  getSupabaseClient: vi.fn(() => null),
  isSupabaseConfigured: vi.fn(() => false),
}))
