import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TopNav } from '@/components/layout/TopNav'
import { renderWithProviders, clearAuthStorage } from './test-utils'

vi.mock('@/hooks/useNotifications', () => ({
  useUnreadNotificationCount: vi.fn(),
  useNotifications: vi.fn(),
  useMarkNotificationsRead: vi.fn(),
  useNotificationAction: vi.fn(),
}))

import { useUnreadNotificationCount } from '@/hooks/useNotifications'

describe('TopNav', () => {
  beforeEach(() => {
    clearAuthStorage()
    vi.mocked(useUnreadNotificationCount).mockReturnValue({
      data: 0,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useUnreadNotificationCount>)
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

  it('shows unread badge when count is greater than zero', () => {
    vi.mocked(useUnreadNotificationCount).mockReturnValue({
      data: 3,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useUnreadNotificationCount>)

    renderWithProviders(<TopNav />, { authenticated: true })

    expect(screen.getByRole('link', { name: /notifications, 3 unread/i })).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('caps badge display at 9+', () => {
    vi.mocked(useUnreadNotificationCount).mockReturnValue({
      data: 12,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useUnreadNotificationCount>)

    renderWithProviders(<TopNav />, { authenticated: true })

    expect(screen.getByRole('link', { name: /notifications, 12 unread/i })).toBeInTheDocument()
    expect(screen.getByText('9+')).toBeInTheDocument()
  })
})
