import { screen } from '@testing-library/react'
import { renderApp, clearAuthStorage } from './test-utils'

describe('routes', () => {
  beforeEach(() => {
    clearAuthStorage()
  })

  const protectedRoutes: Array<{ path: string; heading: RegExp }> = [
    { path: '/', heading: /^dashboard$/i },
    { path: '/list', heading: /all products/i },
    { path: '/products/abc-123', heading: /product detail/i },
    { path: '/products/abc-123/variants', heading: /choose variant/i },
    { path: '/notifications', heading: /^notifications$/i },
    { path: '/history', heading: /^history$/i },
    { path: '/settings', heading: /^settings$/i },
  ]

  it.each(protectedRoutes)('renders $path with correct heading', async ({ path, heading }) => {
    renderApp(path, { authenticated: true })
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  })

  it('renders NotFoundPage for unknown routes', async () => {
    renderApp('/does-not-exist', { authenticated: true })
    expect(await screen.findByRole('heading', { name: /page not found/i })).toBeInTheDocument()
  })

  it('login page is accessible without auth', async () => {
    renderApp('/login', { authenticated: false })
    expect(await screen.findByRole('button', { name: /continue with google/i })).toBeDisabled()
  })
})
