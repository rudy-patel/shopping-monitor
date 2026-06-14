import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TopNav } from '@/components/layout/TopNav'
import * as apiModule from '@/lib/api'
import { defaultProfileResponse } from './setup'
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
    vi.spyOn(apiModule, 'apiFetch').mockImplementation(async (path, init) => {
      if (path === '/api/profile' && (!init?.method || init.method === 'GET')) {
        return defaultProfileResponse
      }
      if (path === '/api/profile' && init?.method === 'PATCH') {
        return { ...defaultProfileResponse, display_currency: 'USD' }
      }
      throw new Error(`Unexpected apiFetch: ${path}`)
    })
    vi.mocked(useUnreadNotificationCount).mockReturnValue({
      data: 0,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useUnreadNotificationCount>)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders logo, Add Product, bell, and avatar menu without currency control', () => {
    renderWithProviders(<TopNav />, { authenticated: true })

    expect(screen.getByRole('link', { name: /shopping monitor/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add product/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /display currency/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/^display currency$/i)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /notifications/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /account menu/i })).toBeInTheDocument()
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
