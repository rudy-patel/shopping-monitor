import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { clearAuthStorage, renderApp } from './test-utils'

describe('LoginPage', () => {
  beforeEach(() => {
    clearAuthStorage()
  })

  it('does not show top nav on login', async () => {
    renderApp('/login', { authenticated: false })

    expect(await screen.findByRole('button', { name: /continue with google/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /add product/i })).not.toBeInTheDocument()
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
