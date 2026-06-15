import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { makeNeedsReviewListing, makeProductDetail } from './product-fixtures'
import { renderApp } from './test-utils'

const mockAcceptMutate = vi.fn()
const mockRejectMutate = vi.fn()
const mockDeleteMutate = vi.fn()

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn() }),
  Toaster: () => null,
}))

vi.mock('@/hooks/useProducts', () => {
  const stub = () => ({ mutate: vi.fn(), isPending: false })
  return {
    useProduct: vi.fn(),
    useRefreshProduct: vi.fn(stub),
    useArchiveProduct: vi.fn(stub),
    useUpdateProduct: vi.fn(stub),
    useDeleteProduct: vi.fn(stub),
    useCreateProduct: vi.fn(stub),
    useRestoreProduct: vi.fn(stub),
    useAcceptListing: vi.fn(),
    useRejectListing: vi.fn(),
    useDeleteListing: vi.fn(),
  }
})

import {
  useAcceptListing,
  useDeleteListing,
  useProduct,
  useRejectListing,
} from '@/hooks/useProducts'

const primaryListing = makeProductDetail().listings[0]
const reviewOne = makeNeedsReviewListing({ id: 'review-1' })
const reviewTwo = makeNeedsReviewListing({
  id: 'review-2',
  review_reason: 'Likely same SKU',
  review_title: 'Second candidate',
})

const productWithQueue = makeProductDetail({
  id: 'review-product-id',
  needs_review_count: 2,
  listings: [primaryListing, reviewOne, reviewTwo],
})

describe('listing review UI', () => {
  beforeEach(() => {
    mockAcceptMutate.mockClear()
    mockRejectMutate.mockClear()
    mockDeleteMutate.mockClear()

    vi.mocked(useProduct).mockReturnValue({
      data: productWithQueue,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    vi.mocked(useAcceptListing).mockReturnValue({
      mutate: mockAcceptMutate,
      isPending: false,
    } as ReturnType<typeof useAcceptListing>)

    vi.mocked(useRejectListing).mockReturnValue({
      mutate: mockRejectMutate,
      isPending: false,
    } as ReturnType<typeof useRejectListing>)

    vi.mocked(useDeleteListing).mockReturnValue({
      mutate: mockDeleteMutate,
      isPending: false,
    } as ReturnType<typeof useDeleteListing>)
  })

  it('renders review queue cards with reason text', () => {
    renderApp(`/products/${productWithQueue.id}`, { authenticated: true })

    expect(screen.getByRole('heading', { name: /needs review \(2\)/i })).toBeInTheDocument()
    expect(screen.getByText(/same laptop model/i)).toBeInTheDocument()
    expect(screen.getByText(/likely same sku/i)).toBeInTheDocument()
    expect(screen.getByText(/candidate at dime mtl/i)).toBeInTheDocument()
    expect(screen.getByText(/second candidate/i)).toBeInTheDocument()
  })

  it('calls accept mutate when Accept is clicked', async () => {
    const user = userEvent.setup()
    renderApp(`/products/${productWithQueue.id}`, { authenticated: true })

    const acceptButtons = screen.getAllByRole('button', { name: /^accept$/i })
    await user.click(acceptButtons[0])

    expect(mockAcceptMutate).toHaveBeenCalledWith('review-1')
  })

  it('calls reject mutate when Reject is clicked', async () => {
    const user = userEvent.setup()
    renderApp(`/products/${productWithQueue.id}`, { authenticated: true })

    const rejectButtons = screen.getAllByRole('button', { name: /^reject$/i })
    await user.click(rejectButtons[0])

    expect(mockRejectMutate).toHaveBeenCalledWith('review-1')
  })

  it('does not show needs_review rows in the main listings section', () => {
    renderApp(`/products/${productWithQueue.id}`, { authenticated: true })

    const listingsHeading = screen.getByRole('heading', { name: /^listings$/i })
    const listingsSection = listingsHeading.parentElement
    expect(listingsSection).not.toBeNull()
    if (!listingsSection) return
    expect(within(listingsSection).queryByText(/candidate at dime mtl/i)).not.toBeInTheDocument()
    expect(within(listingsSection).getByText(/^best buy canada$/i)).toBeInTheDocument()
  })

  it('shows fallback copy when review_reason is missing', () => {
    const noReason = makeNeedsReviewListing({
      id: 'review-no-reason',
      review_reason: null,
    })
    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({
        id: 'fallback-product',
        needs_review_count: 1,
        listings: [primaryListing, noReason],
      }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    renderApp('/products/fallback-product', { authenticated: true })

    expect(screen.getByText(/possible match/i)).toBeInTheDocument()
  })
})

describe('listing remove on main table', () => {
  beforeEach(() => {
    mockDeleteMutate.mockClear()

    const autoAdded = makeNeedsReviewListing({
      id: 'auto-added-1',
      review_status: 'auto_added',
      match_confidence: 0.91,
      review_reason: null,
      review_title: null,
    })

    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({
        id: 'remove-product-id',
        listings: [primaryListing, autoAdded],
        listing_count: 2,
      }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    vi.mocked(useAcceptListing).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useAcceptListing>)

    vi.mocked(useRejectListing).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useRejectListing>)

    vi.mocked(useDeleteListing).mockReturnValue({
      mutate: mockDeleteMutate,
      isPending: false,
    } as ReturnType<typeof useDeleteListing>)
  })

  it('fires delete mutate for auto_added non-primary listing', async () => {
    const user = userEvent.setup()
    renderApp('/products/remove-product-id', { authenticated: true })

    await user.click(screen.getByRole('button', { name: /^remove$/i }))

    expect(mockDeleteMutate).toHaveBeenCalledWith('auto-added-1')
  })
})
