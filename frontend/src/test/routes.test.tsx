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

import { useProduct } from '@/hooks/useProducts'

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
    { path: '/notifications', heading: /^notifications$/i },
    { path: '/history', heading: /archived products/i },
    { path: '/settings', heading: /^settings$/i },
  ]

  it.each(protectedRoutes)('renders $path with correct heading', async ({ path, heading, setup }) => {
    setup?.()
    renderApp(path, { authenticated: true })
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
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
