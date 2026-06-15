import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { clearJustAddedProduct } from '@/lib/just-added-product'
import { makeProductDetail } from './product-fixtures'
import { renderApp } from './test-utils'

const mockRefreshMutate = vi.fn()
const mockUpdateMutate = vi.fn()

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
    useAcceptListing: vi.fn(stub),
    useRejectListing: vi.fn(stub),
    useDeleteListing: vi.fn(stub),
  }
})

import {
  useProduct,
  useRefreshProduct,
  useArchiveProduct,
  useUpdateProduct,
  useRestoreProduct,
} from '@/hooks/useProducts'

const product = makeProductDetail({
  id: 'detail-product-id',
  notification_threshold_pct: 10,
  effective_threshold_pct: 20,
})

describe('ProductDetailPage', () => {
  beforeEach(() => {
    clearJustAddedProduct()
    mockRefreshMutate.mockClear()
    mockUpdateMutate.mockClear()

    vi.mocked(useProduct).mockReturnValue({
      data: product,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    vi.mocked(useRefreshProduct).mockReturnValue({
      mutate: mockRefreshMutate,
      isPending: false,
    } as ReturnType<typeof useRefreshProduct>)

    vi.mocked(useUpdateProduct).mockReturnValue({
      mutate: mockUpdateMutate,
      isPending: false,
    } as ReturnType<typeof useUpdateProduct>)

    vi.mocked(useArchiveProduct).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useArchiveProduct>)

    vi.mocked(useRestoreProduct).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useRestoreProduct>)
  })

  it('PATCHes threshold and category and calls refresh', async () => {
    const user = userEvent.setup()
    renderApp(`/products/${product.id}`, { authenticated: true })

    await user.click(screen.getByRole('combobox', { name: /category/i }))
    await user.click(screen.getByRole('option', { name: /^home$/i }))
    expect(mockUpdateMutate).toHaveBeenCalledWith({ category: 'home' })

    const threshold = screen.getByLabelText(/notification threshold/i)
    await user.clear(threshold)
    await user.type(threshold, '25')
    await user.tab()
    expect(mockUpdateMutate).toHaveBeenCalledWith({ notification_threshold_pct: 25 })

    await user.click(screen.getByRole('button', { name: /^refresh$/i }))
    expect(mockRefreshMutate).toHaveBeenCalled()
  })

  it('shows restore and archived back link for archived products', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({ id: 'detail-product-id', status: 'archived' }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    renderApp(`/products/${product.id}`, { authenticated: true })

    expect(screen.getByText(/this product is archived/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to archived/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^restore$/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^archive$/i })).not.toBeInTheDocument()
  })

  it('shows cooldown toast when refresh hits rate limit', async () => {
    vi.mocked(useRefreshProduct).mockReturnValue({
      mutate: () => toast('Refresh is on cooldown. Try again in about an hour.'),
      isPending: false,
    } as ReturnType<typeof useRefreshProduct>)

    const user = userEvent.setup()
    renderApp(`/products/${product.id}`, { authenticated: true })

    await user.click(screen.getByRole('button', { name: /^refresh$/i }))
    expect(toast).toHaveBeenCalledWith('Refresh is on cooldown. Try again in about an hour.')
  })

  it('renders hero best price, retailer, trend chip, and a sparkline svg', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({
        id: 'detail-product-id',
        best_price_cents: 27999,
        best_retailer_slug: 'bestbuy_ca',
        price_history_30d: [
          { observed_on: '2026-06-01', price_cents: 28999 },
          { observed_on: '2026-06-14', price_cents: 27999 },
        ],
      }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    renderApp(`/products/${product.id}`, { authenticated: true })

    const heroPrice = screen
      .getAllByText('$279.99')
      .find((el) => el.className.includes('text-3xl'))
    expect(heroPrice).toBeDefined()
    expect(screen.getByText(/at Best Buy Canada/i)).toBeInTheDocument()
    const sparkline = screen.getByRole('img')
    expect(sparkline.tagName.toLowerCase()).toBe('svg')
    expect(sparkline.querySelector('title')?.textContent).toMatch(/30-day price trend/)
    expect(screen.queryByText('Best price')).not.toBeInTheDocument()
    expect(screen.queryByText(/vs best/i)).not.toBeInTheDocument()
  })

  it('sorts listings cheapest-first with best-price hints and no scrape badges', () => {
    const primary = product.listings[0]
    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({
        id: 'detail-product-id',
        listings: [
          { ...primary, id: 'primary', last_known_price_cents: 12999, retailer_slug: 'bestbuy_ca' },
          {
            ...primary,
            id: 'cheap',
            is_primary: false,
            review_status: 'auto_added',
            last_known_price_cents: 11999,
            retailer_slug: 'amazon_ca',
          },
          {
            ...primary,
            id: 'expensive',
            is_primary: false,
            review_status: 'auto_added',
            last_known_price_cents: 13999,
            retailer_slug: 'apple_ca',
          },
        ],
      }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    renderApp(`/products/${product.id}`, { authenticated: true })

    const listingsSection = screen.getByRole('region', { name: /^listings$/i })
    const openLinks = within(listingsSection)
      .getAllByRole('link', { name: /^open on /i })
      .map((node) => node.textContent?.replace(/\s*$/, ''))
    expect(openLinks).toEqual([
      'Open on Amazon.ca',
      'Open on Best Buy Canada',
      'Open on Apple Canada',
    ])
    expect(within(listingsSection).getByText('Best price')).toBeInTheDocument()
    expect(within(listingsSection).getByText('+$10.00 vs best')).toBeInTheDocument()
    expect(within(listingsSection).getByText('+$20.00 vs best')).toBeInTheDocument()
    expect(within(listingsSection).queryByText('ok')).not.toBeInTheDocument()
  })
})
