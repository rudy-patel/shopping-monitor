import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VariantPickerPage } from '@/pages/VariantPickerPage'
import { makeProductDetail } from './product-fixtures'
import { renderWithProviders } from './test-utils'

const mockSelectMutate = vi.fn()
const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/hooks/useProducts', () => ({
  useProduct: vi.fn(),
  useSelectVariant: vi.fn(),
}))

import { useProduct, useSelectVariant } from '@/hooks/useProducts'

const needsInputProduct = makeProductDetail({
  id: 'variant-product',
  status: 'needs_input',
  listings: [
    {
      id: 'listing-1',
      retailer_slug: 'bestbuy_ca',
      url: 'https://fixtures.local/bestbuy_ca/multi_variant',
      variant_attributes: {},
      available_variants: [
        {
          attributes: [
            { attribute_name: 'Colour', attribute_value: 'Pink' },
            { attribute_name: 'Colour', attribute_value: 'Graphite' },
          ],
          sku: 'pink-sku',
        },
        {
          attributes: [{ attribute_name: 'Colour', attribute_value: 'Graphite' }],
          sku: 'graphite-sku',
        },
      ],
      is_primary: true,
      review_status: 'accepted',
      last_known_price_cents: 9999,
      is_in_stock: true,
      last_scraped_at: '2026-06-13T12:00:00.000Z',
      scrape_status: 'ok',
      match_confidence: null,
    },
  ],
})

describe('VariantPickerPage', () => {
  beforeEach(() => {
    mockSelectMutate.mockClear()
    mockNavigate.mockClear()

    vi.mocked(useProduct).mockReturnValue({
      data: needsInputProduct,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    vi.mocked(useSelectVariant).mockReturnValue({
      mutate: mockSelectMutate,
      isPending: false,
    } as ReturnType<typeof useSelectVariant>)
  })

  it('renders variant options and calls select API', async () => {
    const user = userEvent.setup()
    renderWithProviders(<VariantPickerPage />, {
      authenticated: true,
      route: `/products/${needsInputProduct.id}/variants`,
      routerProps: { initialEntries: [`/products/${needsInputProduct.id}/variants`] },
    })

    expect(screen.getByText(/pick the version you want to track/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pink · graphite/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^graphite$/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^graphite$/i }))
    expect(mockSelectMutate).toHaveBeenCalledWith({ colour: 'Graphite' })
  })

  it('redirects to detail when product is not needs_input', async () => {
    vi.mocked(useProduct).mockReturnValue({
      data: makeProductDetail({ id: 'active', status: 'active' }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useProduct>)

    renderWithProviders(<VariantPickerPage />, {
      authenticated: true,
      route: '/products/active/variants',
      routerProps: { initialEntries: ['/products/active/variants'] },
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/products/active', { replace: true })
    })
  })
})
