import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { AddProductDialog } from '@/components/add-product/AddProductDialog'
import { useCreateProduct } from '@/hooks/useProducts'
import { IN_STOCK_URL, MULTI_VARIANT_URL } from './product-fixtures'
import { renderWithProviders } from './test-utils'

const mockNavigate = vi.fn()

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn() }),
  Toaster: () => null,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/hooks/useProducts', () => ({
  useCreateProduct: vi.fn(),
}))

describe('AddProductDialog', () => {
  const mockMutate = vi.fn()

  beforeEach(() => {
    vi.mocked(toast).mockClear()
    vi.mocked(toast.error).mockClear()
    mockMutate.mockClear()
    mockNavigate.mockClear()
    vi.mocked(useCreateProduct).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as ReturnType<typeof useCreateProduct>)
  })

  it('sends URL and category on submit', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()

    renderWithProviders(
      <AddProductDialog open onOpenChange={onOpenChange} />,
      { authenticated: true },
    )

    await user.type(screen.getByLabelText(/product url/i), IN_STOCK_URL)
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    expect(mockMutate).toHaveBeenCalledWith({
      url: IN_STOCK_URL,
      category: 'auto',
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('routes to variants when created product needs input', async () => {
    mockMutate.mockImplementation(() => {
      mockNavigate('/products/needs-input-id/variants')
    })

    const user = userEvent.setup()
    renderWithProviders(
      <AddProductDialog open onOpenChange={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByLabelText(/product url/i), MULTI_VARIANT_URL)
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/products/needs-input-id/variants')
    })
  })

  it('routes to detail for active products', async () => {
    mockMutate.mockImplementation(() => {
      mockNavigate('/products/active-id')
    })

    const user = userEvent.setup()
    renderWithProviders(
      <AddProductDialog open onOpenChange={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByLabelText(/product url/i), IN_STOCK_URL)
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/products/active-id')
    })
  })

  it('shows error toast on API failure via mutation hook', async () => {
    vi.mocked(useCreateProduct).mockReturnValue({
      mutate: () => toast.error('Not a Canadian listing'),
      isPending: false,
    } as ReturnType<typeof useCreateProduct>)

    const user = userEvent.setup()
    renderWithProviders(
      <AddProductDialog open onOpenChange={vi.fn()} />,
      { authenticated: true },
    )

    await user.type(screen.getByLabelText(/product url/i), IN_STOCK_URL)
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    expect(toast.error).toHaveBeenCalledWith('Not a Canadian listing')
  })
})
