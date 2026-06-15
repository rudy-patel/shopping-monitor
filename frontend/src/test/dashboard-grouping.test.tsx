import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DashboardPage } from '@/pages/DashboardPage'
import { makeProductSummary } from './product-fixtures'
import { renderWithProviders } from './test-utils'

vi.mock('@/hooks/useProducts', () => ({
  useProducts: vi.fn(),
  useRefreshProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useArchiveProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useReorderDashboardProducts: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useProducts } from '@/hooks/useProducts'

describe('DashboardPage grouping', () => {
  beforeEach(() => {
    localStorage.removeItem('dashboard-collapsed-categories')
    localStorage.removeItem('dashboard-category-order')
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

  it('groups products under category headers and shows empty categories', () => {
    renderWithProviders(<DashboardPage />, { authenticated: true })

    expect(screen.getByRole('button', { name: /shoes · 1/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /tech · 2/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /clothing · 0/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /home · 0/i })).toBeInTheDocument()
    expect(screen.getByText('Shoe Item')).toBeInTheDocument()
    expect(screen.getByText('Tech Item')).toBeInTheDocument()
    expect(screen.getByText('Another Tech')).toBeInTheDocument()
  })

  it('collapses and expands a category section', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />, { authenticated: true })

    const techToggle = screen.getByRole('button', { name: /tech · 2/i })
    expect(screen.getByText('Tech Item')).toBeVisible()

    await user.click(techToggle)
    expect(screen.queryByText('Tech Item')).not.toBeInTheDocument()

    await user.click(techToggle)
    expect(screen.getByText('Tech Item')).toBeInTheDocument()
  })

  it('shows edit order control', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />, { authenticated: true })
    expect(screen.getByRole('button', { name: /edit order/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /edit order/i }))
    expect(screen.getByRole('button', { name: /^done$/i })).toBeInTheDocument()
  })
})
