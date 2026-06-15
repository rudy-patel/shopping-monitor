export type ProductCategory = 'clothing' | 'shoes' | 'home' | 'tech' | 'other'

export type CategoryInput = 'auto' | ProductCategory

export const CATEGORY_ORDER: ProductCategory[] = [
  'clothing',
  'shoes',
  'home',
  'tech',
  'other',
]

export const CATEGORY_LABELS: Record<ProductCategory, string> = {
  clothing: 'Clothing',
  shoes: 'Shoes',
  home: 'Home',
  tech: 'Tech',
  other: 'Other',
}

export const ADD_PRODUCT_CATEGORIES: { value: CategoryInput; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'clothing', label: 'Clothing' },
  { value: 'shoes', label: 'Shoes' },
  { value: 'home', label: 'Home' },
  { value: 'tech', label: 'Tech' },
  { value: 'other', label: 'Other' },
]

export function categoryLabel(slug: ProductCategory): string {
  return CATEGORY_LABELS[slug] ?? slug
}

export function groupByCategory<T extends { category: ProductCategory }>(
  items: T[],
): Map<ProductCategory, T[]> {
  const grouped = new Map<ProductCategory, T[]>()
  for (const category of CATEGORY_ORDER) {
    grouped.set(category, [])
  }
  for (const item of items) {
    const bucket = grouped.get(item.category)
    if (bucket) {
      bucket.push(item)
    }
  }
  return grouped
}

export function sortProductsInCategory<T extends { dashboard_sort_order?: number | null; created_at: string }>(
  items: T[],
): T[] {
  const ordered = items.filter((item) => item.dashboard_sort_order != null)
  const unordered = items.filter((item) => item.dashboard_sort_order == null)
  ordered.sort(
    (a, b) => (a.dashboard_sort_order ?? 0) - (b.dashboard_sort_order ?? 0),
  )
  unordered.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
  return [...ordered, ...unordered]
}
