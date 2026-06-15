import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HistoryPage } from '@/pages/HistoryPage'
import { makeProductSummary } from './product-fixtures'
import { renderWithProviders } from './test-utils'

const mockRestoreMutate = vi.fn()

vi.mock('@/hooks/useProducts', () => ({
  useProducts: vi.fn(),
  useRestoreProduct: vi.fn(),
  useDeleteProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useProducts, useRestoreProduct } from '@/hooks/useProducts'

const archived = makeProductSummary({
  id: 'archived-1',
  title: 'Archived Keyboard',
  status: 'archived',
})

describe('HistoryPage restore', () => {
  beforeEach(() => {
    mockRestoreMutate.mockClear()
    vi.mocked(useProducts).mockReturnValue({
      data: [archived],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProducts>)
    vi.mocked(useRestoreProduct).mockReturnValue({
      mutate: mockRestoreMutate,
      isPending: false,
    } as ReturnType<typeof useRestoreProduct>)
  })

  it('lists archived products and restores on button click', async () => {
    const user = userEvent.setup()
    renderWithProviders(<HistoryPage />, { authenticated: true })

    expect(screen.getByRole('heading', { name: /^archived$/i })).toBeInTheDocument()
    expect(screen.getByText('Archived Keyboard')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^restore$/i }))
    expect(mockRestoreMutate).toHaveBeenCalled()
  })

  it('shows empty state when no archived products', async () => {
    vi.mocked(useProducts).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProducts>)

    renderWithProviders(<HistoryPage />, { authenticated: true })

    await waitFor(() => {
      expect(screen.getByText(/no archived products/i)).toBeInTheDocument()
    })
  })
})
