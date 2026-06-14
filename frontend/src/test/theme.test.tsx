import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useTheme } from '@/contexts/ThemeContext'
import * as apiModule from '@/lib/api'
import { defaultProfileResponse } from './setup'
import { ProviderStack, clearAuthStorage } from './test-utils'

function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme()
  return (
    <button type="button" onClick={toggleTheme}>
      Current theme: {theme}
    </button>
  )
}

function renderThemeTree(authenticated = false) {
  if (authenticated) {
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
  }
  return render(
    <ProviderStack>
      <ThemeToggleButton />
    </ProviderStack>,
  )
}

describe('ThemeContext', () => {
  beforeEach(() => {
    clearAuthStorage()
    document.documentElement.classList.remove('dark')
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>
        return { ...defaultProfileResponse, ...body }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('defaults to light theme', () => {
    renderThemeTree(false)

    expect(screen.getByRole('button', { name: /current theme: light/i })).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('toggles theme and persists to localStorage', async () => {
    const user = userEvent.setup()

    renderThemeTree(false)

    await user.click(screen.getByRole('button', { name: /current theme: light/i }))

    expect(screen.getByRole('button', { name: /current theme: dark/i })).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')

    await user.click(screen.getByRole('button', { name: /current theme: dark/i }))

    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
  })

  it('hydrates theme from profile when authenticated', async () => {
    vi.mocked(apiModule.apiFetch).mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return { ...defaultProfileResponse, theme: 'dark' }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    renderThemeTree(true)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /current theme: dark/i })).toBeInTheDocument()
    })
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('PATCHes profile when theme changes while authenticated', async () => {
    const user = userEvent.setup()
    renderThemeTree(true)

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile')
    })

    await user.click(screen.getByRole('button', { name: /current theme: light/i }))

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ theme: 'dark' }),
      })
    })
  })
})
