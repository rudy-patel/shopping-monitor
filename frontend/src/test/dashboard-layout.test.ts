import { describe, expect, it, beforeEach } from 'vitest'
import { sortProductsInCategory } from '@/lib/categories'
import {
  hasStoredCollapsePreference,
  isCategoryExpanded,
  readCategoryOrder,
  readCollapsedCategories,
  saveCategoryOrder,
  saveCollapsedCategories,
  COLLAPSED_CATEGORIES_KEY,
} from '@/lib/dashboard-layout'

describe('sortProductsInCategory', () => {
  it('orders manual sort first, then newest created_at', () => {
    const sorted = sortProductsInCategory([
      { id: 'a', dashboard_sort_order: 1, created_at: '2026-01-01T00:00:00.000Z' },
      { id: 'b', dashboard_sort_order: 0, created_at: '2026-01-02T00:00:00.000Z' },
      { id: 'c', dashboard_sort_order: null, created_at: '2026-06-01T00:00:00.000Z' },
      { id: 'd', dashboard_sort_order: null, created_at: '2026-05-01T00:00:00.000Z' },
    ])

    expect(sorted.map((item) => item.id)).toEqual(['b', 'a', 'c', 'd'])
  })
})

describe('dashboard layout prefs', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('merges stored category order with defaults for new slugs', () => {
    saveCategoryOrder(['tech', 'shoes', 'home', 'clothing', 'other'])
    expect(readCategoryOrder()).toEqual(['tech', 'shoes', 'home', 'clothing', 'other'])
  })

  it('defaults empty categories to collapsed until a preference is saved', () => {
    expect(hasStoredCollapsePreference()).toBe(false)
    expect(isCategoryExpanded('tech', 2, new Set(), false)).toBe(true)
    expect(isCategoryExpanded('home', 0, new Set(), false)).toBe(false)
  })

  it('respects saved collapse preferences', () => {
    saveCollapsedCategories(new Set(['tech']))
    expect(hasStoredCollapsePreference()).toBe(true)
    expect([...readCollapsedCategories()]).toEqual(['tech'])
    expect(isCategoryExpanded('tech', 2, new Set(['tech']), true)).toBe(false)
    expect(isCategoryExpanded('home', 0, new Set(['tech']), true)).toBe(true)
  })

  it('uses the shared collapsed storage key', () => {
    saveCollapsedCategories(new Set(['shoes']))
    expect(localStorage.getItem(COLLAPSED_CATEGORIES_KEY)).toContain('shoes')
  })
})
