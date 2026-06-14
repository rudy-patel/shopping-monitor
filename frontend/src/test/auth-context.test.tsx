import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { getSupabaseClient } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { PROFILE_QUERY_KEY } from '@/hooks/useProfile'
import { clearAuthStorage, createTestQueryClient, ProviderStack } from './test-utils'
import { createMockSupabaseClient, defaultProfileResponse, mockSignInWithOAuth } from './setup'

function AuthStatus() {
  const { user, isAuthenticated, signInDev, signInWithGoogle, signOut } = useAuth()
  return (
    <div>
      <span>{isAuthenticated ? `signed-in:${user?.email}` : 'signed-out'}</span>
      <button type="button" onClick={signInDev}>
        Dev login
      </button>
      <button type="button" onClick={() => void signInWithGoogle()}>
        Google login
      </button>
      <button type="button" onClick={() => void signOut()}>
        Sign out
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    clearAuthStorage()
    mockSignInWithOAuth.mockReset()
    mockSignInWithOAuth.mockResolvedValue({ data: {}, error: null })
    vi.mocked(getSupabaseClient).mockReturnValue(null)
  })

  it('signInDev sets placeholder user and persists across reload', async () => {
    const user = userEvent.setup()

    render(
      <ProviderStack>
        <AuthStatus />
      </ProviderStack>,
    )

    expect(screen.getByText('signed-out')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /dev login/i }))

    expect(screen.getByText('signed-in:dev@local')).toBeInTheDocument()
    expect(localStorage.getItem('shopping-monitor-dev-auth')).toBe('true')
  })

  it('signOut clears dev session', async () => {
    const user = userEvent.setup()
    localStorage.setItem('shopping-monitor-dev-auth', 'true')

    render(
      <ProviderStack>
        <AuthStatus />
      </ProviderStack>,
    )

    expect(await screen.findByText('signed-in:dev@local')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /sign out/i }))

    expect(screen.getByText('signed-out')).toBeInTheDocument()
    expect(localStorage.getItem('shopping-monitor-dev-auth')).toBeNull()
  })

  it('signOut clears React Query cache', async () => {
    const user = userEvent.setup()
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
    const queryClient = createTestQueryClient()
    queryClient.setQueryData(PROFILE_QUERY_KEY, defaultProfileResponse)

    render(
      <ProviderStack queryClient={queryClient}>
        <AuthStatus />
      </ProviderStack>,
    )

    expect(await screen.findByText('signed-in:dev@local')).toBeInTheDocument()
    expect(queryClient.getQueryData(PROFILE_QUERY_KEY)).toEqual(defaultProfileResponse)

    await user.click(screen.getByRole('button', { name: /sign out/i }))

    expect(screen.getByText('signed-out')).toBeInTheDocument()
    expect(queryClient.getQueryData(PROFILE_QUERY_KEY)).toBeUndefined()
  })

  it('signInWithGoogle calls Supabase OAuth with redirectTo origin', async () => {
    vi.mocked(getSupabaseClient).mockReturnValue(createMockSupabaseClient() as never)
    const user = userEvent.setup()

    render(
      <ProviderStack>
        <AuthStatus />
      </ProviderStack>,
    )

    await user.click(screen.getByRole('button', { name: /google login/i }))

    expect(mockSignInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  })
})
