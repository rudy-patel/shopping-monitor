import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useAuth } from '@/contexts/AuthContext'
import { clearAuthStorage, ProviderStack } from './test-utils'

function AuthStatus() {
  const { user, isAuthenticated, signInDev, signOut } = useAuth()
  return (
    <div>
      <span>{isAuthenticated ? `signed-in:${user?.email}` : 'signed-out'}</span>
      <button type="button" onClick={signInDev}>
        Dev login
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
})
