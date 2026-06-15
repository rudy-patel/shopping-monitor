import { act, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ProductListRow } from '@/components/products/ProductListRow'
import {
  MIN_CATEGORY_THINKING_MS,
  clearJustAddedProduct,
  markProductJustAdded,
} from '@/lib/just-added-product'
import { makeProductSummary } from './product-fixtures'
import { renderWithProviders } from './test-utils'

vi.mock('@/hooks/useProducts', () => ({
  useArchiveProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRefreshProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteProduct: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

vi.mock('@/hooks/useFormatPriceCents', () => ({
  useFormatPriceCents: () => (cents: number | null) =>
    cents === null ? '—' : `$${(cents / 100).toFixed(2)}`,
}))

describe('ProductListRow category sorting badge', () => {
  beforeEach(() => {
    clearJustAddedProduct()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    clearJustAddedProduct()
  })

  it('shows sorting badge for a just-added product on the dashboard row', () => {
    const product = makeProductSummary({ id: 'product-1' })
    markProductJustAdded('product-1', 'llm')

    renderWithProviders(<ProductListRow product={product} />)

    expect(screen.getByTestId('category-sorting-badge')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(MIN_CATEGORY_THINKING_MS)
    })

    expect(screen.queryByTestId('category-sorting-badge')).not.toBeInTheDocument()
  })
})
