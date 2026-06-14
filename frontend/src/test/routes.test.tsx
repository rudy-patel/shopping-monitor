import { screen } from '@testing-library/react'
import { makeProductDetail } from './product-fixtures'
import { renderApp, clearAuthStorage } from './test-utils'

vi.mock('@/hooks/useProducts', () => ({
  useProducts: vi.fn(() => ({ data: [], isLoading: false, isError: false })),
  useProduct: vi.fn(() => ({
    data: makeProductDetail({ id: 'abc-123', title: 'Route Test Product' }),
    isLoading: false,
    isError: false,
  })),
  useRefreshProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useArchiveProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useSelectVariant: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useCreateProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRestoreProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAcceptListing: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRejectListing: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteListing: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

vi.mock('@/hooks/useNotifications', () => ({
  useNotifications: vi.fn(() => ({
    items: [],
    total: 0,
    unreadCount: 0,
    hasMore: false,
    loadMore: vi.fn(),
    isLoading: false,
    isFetching: false,
    isError: false,
    refetch: vi.fn(),
  })),
  useUnreadNotificationCount: vi.fn(() => ({ data: 0 })),
  useMarkNotificationsRead: vi.fn(() => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false })),
  useNotificationAction: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useProduct } from '@/hooks/useProducts'
import { useNotifications } from '@/hooks/useNotifications'

describe('routes', () => {
  beforeEach(() => {
    clearAuthStorage()
    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({ id: 'abc-123', title: 'Route Test Product' }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)
  })

  const protectedRoutes: Array<{ path: string; heading: RegExp; setup?: () => void }> = [
    { path: '/', heading: /your list/i },
    { path: '/list', heading: /all products/i },
    { path: '/products/abc-123', heading: /route test product/i },
    {
      path: '/products/abc-123/variants',
      heading: /route test product/i,
      setup: () => {
        vi.mocked(useProduct).mockReturnValue({
          data: makeProductDetail({ id: 'abc-123', title: 'Route Test Product', status: 'needs_input' }),
          isLoading: false,
          isError: false,
        } as ReturnType<typeof useProduct>)
      },
    },
    { path: '/notifications', heading: /^notifications$/i, setup: () => {
        vi.mocked(useNotifications).mockReturnValue({
          items: [],
          total: 0,
          unreadCount: 0,
          hasMore: false,
          loadMore: vi.fn(),
          isLoading: false,
          isFetching: false,
          isError: false,
          refetch: vi.fn(),
        } as ReturnType<typeof useNotifications>)
      },
    },
    { path: '/history', heading: /archived products/i },
    { path: '/settings', heading: /^settings$/i },
  ]

  it.each(protectedRoutes)('renders $path with correct heading', async ({ path, heading, setup }) => {
    setup?.()
    renderApp(path, { authenticated: true })
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
  })

  it('settings page does not render the T4.2 stub', async () => {
    renderApp('/settings', { authenticated: true })
    expect(await screen.findByRole('heading', { name: /^settings$/i })).toBeInTheDocument()
    expect(screen.queryByText(/coming in t4\.2/i)).not.toBeInTheDocument()
  })

  it('notifications page does not render the T3.3 stub', async () => {
    renderApp('/notifications', { authenticated: true })
    expect(await screen.findByRole('heading', { name: /^notifications$/i })).toBeInTheDocument()
    expect(screen.queryByText(/coming in t3\.3/i)).not.toBeInTheDocument()
  })

  it('renders NotFoundPage for unknown routes', async () => {
    renderApp('/does-not-exist', { authenticated: true })
    expect(await screen.findByRole('heading', { name: /page not found/i })).toBeInTheDocument()
  })

  it('login page is accessible without auth', async () => {
    renderApp('/login', { authenticated: false })
    expect(await screen.findByRole('button', { name: /continue with google/i })).toBeEnabled()
  })
})
