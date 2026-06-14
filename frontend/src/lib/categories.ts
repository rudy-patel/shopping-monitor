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
