import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CategoryField } from '@/components/products/CategoryField'
import {
  MIN_CATEGORY_THINKING_MS,
  clearJustAddedProduct,
  markProductJustAdded,
} from '@/lib/just-added-product'
import { renderWithProviders } from './test-utils'

const mockUpdateMutate = vi.fn()

vi.mock('@/hooks/useProducts', () => ({
  useUpdateProduct: vi.fn(() => ({
    mutate: mockUpdateMutate,
    isPending: false,
  })),
}))

describe('CategoryField thinking UX', () => {
  beforeEach(() => {
    clearJustAddedProduct()
    mockUpdateMutate.mockClear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    clearJustAddedProduct()
  })

  it('shows thinking shimmer then category select for a just-added product', () => {
    markProductJustAdded('product-1', 'llm')

    renderWithProviders(<CategoryField productId="product-1" value="tech" />)

    expect(screen.getByTestId('category-thinking')).toBeInTheDocument()
    expect(screen.queryByTestId('category-select')).not.toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(MIN_CATEGORY_THINKING_MS)
    })

    expect(screen.getByTestId('category-select')).toBeInTheDocument()
    expect(screen.queryByTestId('category-thinking')).not.toBeInTheDocument()
    expect(screen.getByTestId('category-reveal-hint')).toHaveTextContent('Sorted by AI')
  })

  it('renders select immediately when product was not just added', () => {
    renderWithProviders(<CategoryField productId="product-1" value="tech" />)

    expect(screen.getByTestId('category-select')).toBeInTheDocument()
    expect(screen.queryByTestId('category-thinking')).not.toBeInTheDocument()
  })

  it('shows saved-as-picked hint when user chose category manually', () => {
    markProductJustAdded('product-1', 'manual')

    renderWithProviders(<CategoryField productId="product-1" value="home" />)

    act(() => {
      vi.advanceTimersByTime(MIN_CATEGORY_THINKING_MS)
    })

    expect(screen.getByTestId('category-reveal-hint')).toHaveTextContent('Saved as picked')
  })

  it('allows override after thinking completes', async () => {
    vi.useRealTimers()
    markProductJustAdded('product-1', 'llm')
    const user = userEvent.setup()

    renderWithProviders(<CategoryField productId="product-1" value="tech" />)

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, MIN_CATEGORY_THINKING_MS + 50))
    })

    expect(screen.getByTestId('category-select')).toBeInTheDocument()

    await user.click(screen.getByRole('combobox', { name: /category/i }))
    await user.click(screen.getByRole('option', { name: /^home$/i }))

    expect(mockUpdateMutate).toHaveBeenCalledWith({ category: 'home' })
  })
})
