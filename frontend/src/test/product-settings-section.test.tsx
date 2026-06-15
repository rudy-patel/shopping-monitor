import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProductSettingsSection } from '@/components/products/ProductSettingsSection'
import { clearJustAddedProduct, markProductJustAdded } from '@/lib/just-added-product'
import { makeProductDetail } from './product-fixtures'
import { renderWithProviders } from './test-utils'

vi.mock('@/hooks/useProducts', () => ({
  useUpdateProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

describe('ProductSettingsSection', () => {
  const product = makeProductDetail({ id: 'settings-product-id' })

  afterEach(() => {
    clearJustAddedProduct()
  })

  it('renders a collapsible settings region with semantic heading', () => {
    renderWithProviders(<ProductSettingsSection product={product} />)

    expect(screen.getByRole('heading', { level: 2, name: /^settings$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^settings$/i })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.queryByLabelText(/notification threshold/i)).not.toBeInTheDocument()
  })

  it('reveals category and threshold fields when expanded', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ProductSettingsSection product={product} />)

    await user.click(screen.getByRole('button', { name: /^settings$/i }))

    expect(screen.getByRole('region', { name: /^settings$/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/notification threshold/i)).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: /category/i })).toBeInTheDocument()
  })

  it('opens automatically while category thinking is active after add', () => {
    markProductJustAdded(product.id, 'heuristic')
    renderWithProviders(<ProductSettingsSection product={product} />)

    expect(screen.getByRole('button', { name: /^settings$/i })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByTestId('category-thinking')).toBeInTheDocument()
  })
})
