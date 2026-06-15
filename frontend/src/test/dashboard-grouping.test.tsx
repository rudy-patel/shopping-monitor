import { screen } from '@testing-library/react'
import { DashboardPage } from '@/pages/DashboardPage'
import { makeProductSummary } from './product-fixtures'
import { renderWithProviders } from './test-utils'

vi.mock('@/hooks/useProducts', () => ({
  useProducts: vi.fn(),
  useRefreshProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useArchiveProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useProducts } from '@/hooks/useProducts'

describe('DashboardPage grouping', () => {
  beforeEach(() => {
    vi.mocked(useProducts).mockReturnValue({
      data: [
        makeProductSummary({ id: '1', title: 'Tech Item', category: 'tech' }),
        makeProductSummary({ id: '2', title: 'Shoe Item', category: 'shoes' }),
        makeProductSummary({ id: '3', title: 'Another Tech', category: 'tech' }),
      ],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProducts>)
  })

  it('groups products under category headers', () => {
    renderWithProviders(<DashboardPage />, { authenticated: true })

    expect(screen.getByRole('heading', { name: /shoes · 1/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /tech · 2/i })).toBeInTheDocument()
    expect(screen.getByText('Shoe Item')).toBeInTheDocument()
    expect(screen.getByText('Tech Item')).toBeInTheDocument()
    expect(screen.getByText('Another Tech')).toBeInTheDocument()
  })
})
