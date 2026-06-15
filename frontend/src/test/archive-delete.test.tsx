import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProductDetailPage } from '@/pages/ProductDetailPage'
import { makeProductDetail, makeProductSummary } from './product-fixtures'
import { renderWithProviders } from './test-utils'

const mockArchiveMutate = vi.fn()
const mockDeleteMutate = vi.fn()

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() }),
  Toaster: () => null,
}))

vi.mock('@/hooks/useProducts', () => ({
  useProducts: vi.fn(),
  useProduct: vi.fn(),
  useArchiveProduct: vi.fn(),
  useDeleteProduct: vi.fn(),
  useRefreshProduct: vi.fn(),
  useUpdateProduct: vi.fn(),
  useRestoreProduct: vi.fn(),
  useAcceptListing: vi.fn(),
  useRejectListing: vi.fn(),
  useDeleteListing: vi.fn(),
  useReorderDashboardProducts: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import {
  useProducts,
  useProduct,
  useArchiveProduct,
  useDeleteProduct,
  useRefreshProduct,
  useUpdateProduct,
  useRestoreProduct,
  useAcceptListing,
  useRejectListing,
  useDeleteListing,
} from '@/hooks/useProducts'

const activeProduct = makeProductSummary({ id: 'archive-me', title: 'Archive Me' })
const detailProduct = makeProductDetail({ id: 'delete-me', title: 'Delete Me' })

describe('archive and delete flows', () => {
  beforeEach(() => {
    mockArchiveMutate.mockClear()
    mockDeleteMutate.mockClear()
    vi.mocked(toast).mockClear()

    vi.mocked(useProducts).mockReturnValue({
      data: [activeProduct],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProducts>)

    vi.mocked(useProduct).mockReturnValue({
      data: detailProduct,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    vi.mocked(useArchiveProduct).mockReturnValue({
      mutate: mockArchiveMutate,
      isPending: false,
    } as ReturnType<typeof useArchiveProduct>)

    vi.mocked(useDeleteProduct).mockReturnValue({
      mutate: mockDeleteMutate,
      isPending: false,
    } as ReturnType<typeof useDeleteProduct>)

    vi.mocked(useRefreshProduct).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useRefreshProduct>)

    vi.mocked(useUpdateProduct).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useUpdateProduct>)

    vi.mocked(useRestoreProduct).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useRestoreProduct>)

    const listingHookStub = {
      mutate: vi.fn(),
      isPending: false,
    }
    vi.mocked(useAcceptListing).mockReturnValue(
      listingHookStub as ReturnType<typeof useAcceptListing>,
    )
    vi.mocked(useRejectListing).mockReturnValue(
      listingHookStub as ReturnType<typeof useRejectListing>,
    )
    vi.mocked(useDeleteListing).mockReturnValue(
      listingHookStub as ReturnType<typeof useDeleteListing>,
    )
  })

  it('archive removes product from dashboard list via mutation', async () => {
    mockArchiveMutate.mockImplementation(() => {
      vi.mocked(useProducts).mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useProducts>)
      toast.success('Product archived')
    })

    const user = userEvent.setup()
    const { rerender } = renderWithProviders(<DashboardPage />, { authenticated: true })

    expect(screen.getByText('Archive Me')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /product actions/i }))
    await user.click(screen.getByRole('menuitem', { name: /archive/i }))

    expect(mockArchiveMutate).toHaveBeenCalled()
    rerender(<DashboardPage />)
    await waitFor(() => {
      expect(screen.queryByText('Archive Me')).not.toBeInTheDocument()
    })
  })

  it('delete confirms and removes product', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ProductDetailPage />, {
      authenticated: true,
      route: `/products/${detailProduct.id}`,
      routerProps: { initialEntries: [`/products/${detailProduct.id}`] },
    })

    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    expect(mockDeleteMutate).toHaveBeenCalledWith(detailProduct.id)
  })
})
