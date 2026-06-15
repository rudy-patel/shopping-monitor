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

  it('sends auto category by default and closes on success', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()

    mockMutate.mockImplementation((_payload, options) => {
      options?.onSuccess?.()
    })

    renderWithProviders(
      <AddProductDialog open onOpenChange={onOpenChange} />,
      { authenticated: true },
    )

    await user.type(screen.getByLabelText(/product url/i), IN_STOCK_URL)
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    expect(mockMutate).toHaveBeenCalledWith(
      { url: IN_STOCK_URL, category: 'auto' },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    )
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })

  it('keeps modal open while mutation is pending', async () => {
    vi.mocked(useCreateProduct).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
    } as ReturnType<typeof useCreateProduct>)

    renderWithProviders(
      <AddProductDialog open onOpenChange={vi.fn()} />,
      { authenticated: true },
    )

    expect(screen.getByRole('button', { name: /adding/i })).toBeDisabled()
  })

  it('sends manual category when user expands override', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <AddProductDialog open onOpenChange={vi.fn()} />,
      { authenticated: true },
    )

    await user.click(screen.getByRole('button', { name: /set category manually/i }))
    await user.click(screen.getByRole('combobox', { name: /category/i }))
    await user.click(screen.getByRole('option', { name: /^home$/i }))
    await user.type(screen.getByLabelText(/product url/i), IN_STOCK_URL)
    await user.click(screen.getByRole('button', { name: /^add$/i }))

    expect(mockMutate).toHaveBeenCalledWith(
      { url: IN_STOCK_URL, category: 'home' },
      expect.any(Object),
    )
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
