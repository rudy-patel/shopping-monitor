import { render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { clearAuthStorage, ProviderStack } from './test-utils'

function ProtectedContent() {
  return <h1>Protected Content</h1>
}

function renderProtectedRoute(initialPath: string, authenticated: boolean) {
  if (authenticated) {
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
  }

  const memoryRouter = createMemoryRouter(
    [
      { path: '/login', element: <h1>Login</h1> },
      {
        element: <ProtectedRoute />,
        children: [{ path: '/settings', element: <ProtectedContent /> }],
      },
    ],
    { initialEntries: [initialPath] },
  )

  render(
    <ProviderStack>
      <RouterProvider router={memoryRouter} />
    </ProviderStack>,
  )

  return memoryRouter
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    clearAuthStorage()
  })

  it('redirects unauthenticated users to login and preserves intended path', async () => {
    const memoryRouter = renderProtectedRoute('/settings', false)

    expect(await screen.findByRole('heading', { name: /login/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(memoryRouter.state.location.pathname).toBe('/login')
      expect(memoryRouter.state.location.state).toEqual({ from: '/settings' })
    })
  })

  it('renders child route when authenticated', async () => {
    renderProtectedRoute('/settings', true)

    expect(await screen.findByRole('heading', { name: /protected content/i })).toBeInTheDocument()
  })
})
