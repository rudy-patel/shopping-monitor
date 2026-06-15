import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CATEGORY_REVEAL_HINT_MS,
  MIN_CATEGORY_THINKING_MS,
  clearJustAddedProduct,
  markProductJustAdded,
  revealHintLabel,
  useJustAddedCategoryThinking,
} from '@/lib/just-added-product'

describe('just-added-product session', () => {
  beforeEach(() => {
    clearJustAddedProduct()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    clearJustAddedProduct()
  })

  it('marks and clears session storage', () => {
    markProductJustAdded('product-1', 'llm')
    expect(sessionStorage.getItem('shopping-monitor:just-added-product')).toContain('product-1')

    clearJustAddedProduct()
    expect(sessionStorage.getItem('shopping-monitor:just-added-product')).toBeNull()
  })

  it('shows thinking then reveal hint for the marked product', () => {
    markProductJustAdded('product-1', 'llm')

    const { result } = renderHook(() => useJustAddedCategoryThinking('product-1'))

    expect(result.current.isThinking).toBe(true)
    expect(result.current.showRevealHint).toBe(false)

    act(() => {
      vi.advanceTimersByTime(MIN_CATEGORY_THINKING_MS)
    })

    expect(result.current.isThinking).toBe(false)
    expect(result.current.showRevealHint).toBe(true)

    act(() => {
      vi.advanceTimersByTime(CATEGORY_REVEAL_HINT_MS)
    })

    expect(result.current.isThinking).toBe(false)
    expect(result.current.showRevealHint).toBe(false)
    expect(sessionStorage.getItem('shopping-monitor:just-added-product')).toBeNull()
  })

  it('ignores unrelated product ids', () => {
    markProductJustAdded('product-1', 'llm')

    const { result } = renderHook(() => useJustAddedCategoryThinking('other-id'))

    expect(result.current.isThinking).toBe(false)
    expect(result.current.showRevealHint).toBe(false)
  })

  it('uses manual reveal copy when category was picked by user', () => {
    expect(revealHintLabel('manual')).toBe('Saved as picked')
    expect(revealHintLabel('llm')).toBe('Sorted by AI')
  })
})
