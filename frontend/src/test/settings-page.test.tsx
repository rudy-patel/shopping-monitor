import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { SettingsPage } from '@/pages/SettingsPage'
import * as apiModule from '@/lib/api'
import { defaultProfileResponse } from './setup'
import { renderWithProviders, clearAuthStorage } from './test-utils'

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn() }),
}))

describe('SettingsPage', () => {
  beforeEach(() => {
    clearAuthStorage()
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>
        return { ...defaultProfileResponse, ...body }
      }
      if (path === '/api/account' && init?.method === 'DELETE') {
        return undefined
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders sections when profile loads', async () => {
    renderWithProviders(<SettingsPage />, { authenticated: true })

    expect(await screen.findByRole('heading', { level: 1, name: /^settings$/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /^display$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^notifications$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^revisit prompts$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^account$/i })).toBeInTheDocument()
    expect(screen.queryByText(/coming in t4\.2/i)).not.toBeInTheDocument()
  })

  it('changes currency via PATCH', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    await screen.findByRole('heading', { name: /^display$/i })
    await user.click(screen.getByRole('radio', { name: /^usd$/i }))

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ display_currency: 'USD' }),
      })
    })
    expect(localStorage.getItem('display-currency')).toBe('USD')
  })

  it('toggles notifications via PATCH', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const toggle = await screen.findByRole('switch', { name: /in-app notifications/i })
    expect(toggle).toBeChecked()
    await user.click(toggle)

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ notifications_enabled: false }),
      })
    })
  })

  it('saves valid default threshold on blur and reverts invalid input', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const input = await screen.findByLabelText(/default threshold/i)
    await user.clear(input)
    await user.type(input, '25')
    await user.tab()

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ default_threshold_pct: 25 }),
      })
    })

    vi.mocked(apiModule.apiFetch).mockClear()
    await user.clear(input)
    await user.type(input, '999')
    await user.tab()

    expect(input).toHaveValue(25)
    expect(apiModule.apiFetch).not.toHaveBeenCalled()
  })

  it('toggles email digest via PATCH', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const toggle = await screen.findByRole('switch', { name: /daily email digest/i })
    await user.click(toggle)

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ email_digest_enabled: false }),
      })
    })
  })

  it('toggles theme and PATCHes profile', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const toggle = await screen.findByRole('switch', { name: /dark mode/i })
    expect(toggle).not.toBeChecked()
    await user.click(toggle)

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ theme: 'dark' }),
      })
    })
  })

  it('hydrates theme from profile on mount', async () => {
    vi.mocked(apiModule.apiFetch).mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return { ...defaultProfileResponse, theme: 'dark' }
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>
        return { ...defaultProfileResponse, theme: 'dark', ...body }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    renderWithProviders(<SettingsPage />, { authenticated: true })

    const toggle = await screen.findByRole('switch', { name: /dark mode/i })
    await waitFor(() => {
      expect(toggle).toBeChecked()
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  it('disables revisit child controls when master is off', async () => {
    vi.mocked(apiModule.apiFetch).mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return { ...defaultProfileResponse, revisit_prompts_enabled: false }
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>
        return { ...defaultProfileResponse, revisit_prompts_enabled: false, ...body }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    renderWithProviders(<SettingsPage />, { authenticated: true })

    expect(await screen.findByRole('switch', { name: /^revisit prompts$/i })).not.toBeChecked()
    expect(screen.getByRole('switch', { name: /on-sale nudges/i })).toBeDisabled()
    expect(screen.getByRole('switch', { name: /stale-list nudges/i })).toBeDisabled()
    expect(screen.getByLabelText(/days on list before a stale check-in/i)).toBeDisabled()
  })

  it('saves revisit stale days on blur', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const input = await screen.findByLabelText(/days on list before a stale check-in/i)
    await user.clear(input)
    await user.type(input, '45')
    await user.tab()

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify({ revisit_stale_days: 45 }),
      })
    })
  })

  it('reverts notification toggle on PATCH failure', async () => {
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        throw new apiModule.ApiError(500, 'save failed')
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const toggle = await screen.findByRole('switch', { name: /in-app notifications/i })
    await user.click(toggle)

    await waitFor(() => {
      expect(toggle).toBeChecked()
    })
  })

  it('opens delete account dialog and calls DELETE /api/account on confirm', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    const deleteButton = await screen.findByRole('button', { name: /delete account/i })
    expect(deleteButton).toBeEnabled()
    expect(
      screen.queryByText(/account deletion will be available in a follow-up update/i),
    ).not.toBeInTheDocument()

    await user.click(deleteButton)

    expect(await screen.findByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText(/this permanently removes your products/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    await waitFor(() => {
      expect(apiModule.apiFetch).toHaveBeenCalledWith('/api/account', { method: 'DELETE' })
    })
  })

  it('shows toast and stays on settings when delete account fails', async () => {
    vi.mocked(toast.error).mockClear()
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>
        return { ...defaultProfileResponse, ...body }
      }
      if (path === '/api/account' && init?.method === 'DELETE') {
        throw new apiModule.ApiError(502, 'Could not delete account')
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })

    const user = userEvent.setup()
    renderWithProviders(<SettingsPage />, { authenticated: true })

    await user.click(await screen.findByRole('button', { name: /delete account/i }))
    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Could not delete account')
    })
    expect(screen.getByRole('heading', { level: 1, name: /^settings$/i })).toBeInTheDocument()
  })
})
