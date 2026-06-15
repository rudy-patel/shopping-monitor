import { screen } from '@testing-library/react'
import { renderApp, clearAuthStorage } from './test-utils'

describe('App', () => {
  beforeEach(() => {
    clearAuthStorage()
  })

  it('redirects unauthenticated users to login', async () => {
    renderApp('/', { authenticated: false })

    expect(await screen.findByRole('heading', { name: /someday/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeEnabled()
  })

  it('shows top nav and dashboard when authenticated', async () => {
    renderApp('/', { authenticated: true })

    expect(await screen.findByRole('heading', { name: /your list/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /someday/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add product/i })).toBeInTheDocument()
  })
})
