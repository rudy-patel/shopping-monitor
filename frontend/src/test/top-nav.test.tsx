import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TopNav } from '@/components/layout/TopNav'
import { renderWithProviders, clearAuthStorage } from './test-utils'

describe('TopNav', () => {
  beforeEach(() => {
    clearAuthStorage()
  })

  it('renders logo, Add Product, currency switcher, bell, and avatar menu', () => {
    renderWithProviders(<TopNav />, { authenticated: true })

    expect(screen.getByRole('link', { name: /shopping monitor/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add product/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /display currency/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /notifications/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /account menu/i })).toBeInTheDocument()
  })

  it('updates currency context and localStorage when currency is changed', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TopNav />, { authenticated: true })

    await user.click(screen.getByRole('button', { name: /display currency/i }))
    await user.click(await screen.findByRole('menuitemradio', { name: /usd/i }))

    expect(screen.getByRole('button', { name: /display currency/i })).toHaveTextContent('USD')
    expect(localStorage.getItem('display-currency')).toBe('USD')
  })
})
