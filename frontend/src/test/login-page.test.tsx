import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { getSupabaseClient } from '@/lib/supabase'
import { clearAuthStorage, renderApp } from './test-utils'
import { createMockSupabaseClient, mockSignInWithOAuth } from './setup'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

import { toast } from 'sonner'

describe('LoginPage', () => {
  beforeEach(() => {
    clearAuthStorage()
    mockSignInWithOAuth.mockReset()
    mockSignInWithOAuth.mockResolvedValue({ data: {}, error: null })
    vi.mocked(getSupabaseClient).mockReturnValue(null)
  })

  it('does not show top nav on login', async () => {
    renderApp('/login', { authenticated: false })

    const googleButton = await screen.findByRole('button', { name: /continue with google/i })
    expect(googleButton).toBeInTheDocument()
    expect(googleButton).toBeEnabled()
    expect(screen.queryByRole('button', { name: /add product/i })).not.toBeInTheDocument()
  })

  it('renders the Someday brand pill as the page heading', async () => {
    renderApp('/login', { authenticated: false })

    const heading = await screen.findByRole('heading', { level: 1, name: /someday\.?/i })
    expect(heading).toBeInTheDocument()
  })

  it('exposes a single main landmark (RootLayout wrapper only)', async () => {
    renderApp('/login', { authenticated: false })

    await screen.findByRole('button', { name: /continue with google/i })
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('calls signInWithOAuth when Continue with Google is clicked', async () => {
    vi.mocked(getSupabaseClient).mockReturnValue(createMockSupabaseClient() as never)
    const user = userEvent.setup()
    renderApp('/login', { authenticated: false })

    await user.click(await screen.findByRole('button', { name: /continue with google/i }))

    expect(mockSignInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  })

  it('shows error toast when OAuth fails', async () => {
    vi.mocked(getSupabaseClient).mockReturnValue(createMockSupabaseClient() as never)
    mockSignInWithOAuth.mockRejectedValue(new Error('oauth failed'))
    const user = userEvent.setup()
    renderApp('/login', { authenticated: false })

    await user.click(await screen.findByRole('button', { name: /continue with google/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Could not start Google sign-in. Please try again.')
    })
  })

  it('dev login redirects to preserved path after auth gate', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/login', {
      authenticated: false,
      state: { from: '/settings' },
    })

    await user.click(await screen.findByRole('button', { name: /dev login/i }))

    expect(await screen.findByRole('heading', { name: /^settings$/i })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/settings')
  })
})
