import { CATEGORY_ORDER, type ProductCategory } from '@/lib/categories'

const CATEGORY_ORDER_KEY = 'dashboard-category-order'
export const COLLAPSED_CATEGORIES_KEY = 'dashboard-collapsed-categories'

function readJson<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function readCategoryOrder(): ProductCategory[] {
  const stored = readJson<ProductCategory[]>(CATEGORY_ORDER_KEY)
  if (!stored?.length) return [...CATEGORY_ORDER]

  const valid = stored.filter((category): category is ProductCategory =>
    CATEGORY_ORDER.includes(category),
  )
  const missing = CATEGORY_ORDER.filter((category) => !valid.includes(category))
  return [...valid, ...missing]
}

export function saveCategoryOrder(order: ProductCategory[]) {
  writeJson(CATEGORY_ORDER_KEY, order)
}

export function readCollapsedCategories(): Set<ProductCategory> {
  const stored = readJson<ProductCategory[]>(COLLAPSED_CATEGORIES_KEY)
  if (!stored) return new Set()
  return new Set(stored.filter((category) => CATEGORY_ORDER.includes(category)))
}

export function saveCollapsedCategories(collapsed: Set<ProductCategory>) {
  writeJson(COLLAPSED_CATEGORIES_KEY, [...collapsed])
}

export function hasStoredCollapsePreference(): boolean {
  return localStorage.getItem(COLLAPSED_CATEGORIES_KEY) !== null
}

/** Empty categories start collapsed; non-empty start expanded unless user saved a preference. */
export function isCategoryExpanded(
  category: ProductCategory,
  count: number,
  collapsed: Set<ProductCategory>,
  hasStoredCollapsePref: boolean,
): boolean {
  if (hasStoredCollapsePref) {
    return !collapsed.has(category)
  }
  return count > 0
}
