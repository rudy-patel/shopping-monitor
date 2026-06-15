import { axe } from 'vitest-axe'
import { screen } from '@testing-library/react'
import { DashboardPage } from '@/pages/DashboardPage'
import { makeProductDetail, makeProductSummary } from './product-fixtures'
import { renderApp, renderWithProviders } from './test-utils'

vi.mock('@/hooks/useProducts', () => ({
  useProducts: vi.fn(),
  useProduct: vi.fn(),
  useRefreshProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useArchiveProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRestoreProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAcceptListing: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRejectListing: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteListing: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useCreateProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useSelectVariant: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useProducts, useProduct } from '@/hooks/useProducts'

describe('page accessibility', () => {
  beforeEach(() => {
    vi.mocked(useProducts).mockReturnValue({
      data: [makeProductSummary({ title: 'Sample Product' })],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProducts>)

    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail(),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)
  })

  it('dashboard has no axe violations', async () => {
    const { container } = renderWithProviders(<DashboardPage />, { authenticated: true })
    expect(await screen.findByText('Sample Product')).toBeInTheDocument()
    const results = await axe(container)
    expect(results.violations).toHaveLength(0)
  })

  it('product detail has no axe violations', async () => {
    const product = makeProductDetail()
    const { container } = renderApp(`/products/${product.id}`, { authenticated: true })
    expect(await screen.findByRole('heading', { level: 1 })).toBeInTheDocument()
    const results = await axe(container)
    expect(results.violations).toHaveLength(0)
  })
})
