import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useArchiveProduct } from '@/hooks/useProducts'
import { makeProductDetail } from './product-fixtures'

const mockNavigate = vi.fn()
const mockUpdateProduct = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() }),
  Toaster: () => null,
}))

vi.mock('@/lib/products', async () => {
  const actual = await vi.importActual<typeof import('@/lib/products')>('@/lib/products')
  return {
    ...actual,
    updateProduct: (...args: Parameters<typeof actual.updateProduct>) => mockUpdateProduct(...args),
  }
})

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useArchiveProduct', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    mockUpdateProduct.mockReset()
    vi.mocked(toast.success).mockClear()
    vi.mocked(toast.error).mockClear()
  })

  it('shows a success toast and stays on the current page', async () => {
    mockUpdateProduct.mockResolvedValue(
      makeProductDetail({ id: 'product-1', status: 'archived' }),
    )

    const { result } = renderHook(() => useArchiveProduct('product-1'), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.mutate()
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(mockUpdateProduct).toHaveBeenCalledWith('product-1', { status: 'archived' })
    expect(toast.success).toHaveBeenCalledWith('Product archived')
    expect(mockNavigate).not.toHaveBeenCalled()
  })
})
