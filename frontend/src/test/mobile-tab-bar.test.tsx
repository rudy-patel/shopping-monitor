import { screen } from '@testing-library/react'
import { renderApp } from './test-utils'

describe('MobileTabBar', () => {
  it('renders primary navigation tabs on authenticated routes', async () => {
    renderApp('/', { authenticated: true })

    expect(await screen.findByRole('heading', { name: /^wishlist$/i })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: /primary/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^home$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^all$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^alerts$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^settings$/i })).toBeInTheDocument()
  })
})
