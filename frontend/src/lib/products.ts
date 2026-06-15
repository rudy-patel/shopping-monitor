import { apiFetch } from '@/lib/api'
import type { CategoryInput, ProductCategory } from '@/lib/categories'

export type ProductStatus = 'active' | 'archived' | 'needs_input'
export type TrendDirection = 'down' | 'same' | 'up'

export interface TrendChip {
  direction: TrendDirection
  delta_pct: number | null
  days_of_data: number
  label: string
}

export interface VariantAttribute {
  attribute_name: string
  attribute_value: string
}

export interface AvailableVariant {
  attributes: VariantAttribute[]
  sku?: string
}

export interface Listing {
  id: string
  retailer_slug: string
  url: string
  variant_attributes: Record<string, string>
  available_variants: AvailableVariant[] | null
  is_primary: boolean
  review_status: string
  last_known_price_cents: number | null
  is_in_stock: boolean | null
  last_scraped_at: string | null
  scrape_status: string | null
  match_confidence: number | null
  review_title?: string | null
  review_image_url?: string | null
  review_reason?: string | null
}

export interface ProductSummary {
  id: string
  title: string
  brand: string | null
  image_url: string | null
  category: ProductCategory
  category_source: string
  status: ProductStatus
  notification_threshold_pct: number | null
  notifications_enabled: boolean
  discovery_status: string
  last_refresh_at: string | null
  last_user_interaction_at: string | null
  created_at: string
  updated_at: string
  best_price_cents: number | null
  best_retailer_slug: string | null
  trend: TrendChip
  listing_count: number
  effective_threshold_pct: number
  last_scraped_at: string | null
  needs_review_count: number
  dashboard_sort_order: number | null
}

export interface PriceHistoryPoint {
  observed_on: string
  price_cents: number
}

export interface ProductDetail extends ProductSummary {
  listings: Listing[]
  price_history_30d: PriceHistoryPoint[]
}

export interface ProductFilters {
  status?: ProductStatus | 'active'
  category?: ProductCategory
}

export interface DiscoverySeedEntry {
  retailer_slug: string
  url: string
}

export interface CreateProductInput {
  url: string
  category?: CategoryInput
  discovery_seed?: DiscoverySeedEntry[]
}

export interface UpdateProductInput {
  title?: string
  category?: ProductCategory
  notification_threshold_pct?: number
  notifications_enabled?: boolean
  status?: 'active' | 'archived'
}

export interface DashboardReorderEntry {
  id: string
  dashboard_sort_order: number
}

export function reorderDashboardProducts(
  items: DashboardReorderEntry[],
): Promise<void> {
  return apiFetch<void>('/api/products/dashboard-order', {
    method: 'PUT',
    body: JSON.stringify({ items }),
  })
}

export interface VariantOption {
  attributes: Record<string, string>
  label: string
}

export function productsQueryKey(filters: ProductFilters = {}) {
  return ['products', filters] as const
}

export function productQueryKey(id: string) {
  return ['products', id] as const
}

/** True for list caches (`['products', filters]`), false for detail caches (`['products', id]`). */
export function isProductListQueryKey(queryKey: readonly unknown[]): boolean {
  return queryKey.length > 1 && typeof queryKey[1] === 'object' && queryKey[1] !== null
}

export function listProducts(filters: ProductFilters = {}): Promise<ProductSummary[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.category) params.set('category', filters.category)
  const query = params.toString()
  return apiFetch<ProductSummary[]>(`/api/products${query ? `?${query}` : ''}`)
}

export function getProduct(id: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/products/${id}`)
}

export function createProduct(input: CreateProductInput): Promise<ProductDetail> {
  return apiFetch<ProductDetail>('/api/products', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateProduct(id: string, patch: UpdateProductInput): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/products/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
}

export function deleteProduct(id: string): Promise<void> {
  return apiFetch<void>(`/api/products/${id}`, { method: 'DELETE' })
}

export function refreshProduct(id: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/products/${id}/refresh`, { method: 'POST' })
}

export function selectVariant(
  id: string,
  variantAttributes: Record<string, string>,
): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/products/${id}/select-variant`, {
    method: 'POST',
    body: JSON.stringify({ variant_attributes: variantAttributes }),
  })
}

export function acceptListing(productId: string, listingId: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(
    `/api/products/${productId}/listings/${listingId}/accept`,
    { method: 'POST' },
  )
}

export function rejectListing(productId: string, listingId: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(
    `/api/products/${productId}/listings/${listingId}/reject`,
    { method: 'POST' },
  )
}

export function deleteListing(productId: string, listingId: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/products/${productId}/listings/${listingId}`, {
    method: 'DELETE',
  })
}

export function activeListings(listings: Listing[]): Listing[] {
  return listings
    .filter(
      (listing) =>
        listing.review_status !== 'needs_review' && listing.review_status !== 'rejected',
    )
    .sort((a, b) => {
      const aPrice = a.last_known_price_cents ?? Number.MAX_SAFE_INTEGER
      const bPrice = b.last_known_price_cents ?? Number.MAX_SAFE_INTEGER
      return aPrice - bPrice
    })
}

/** Lowest known price among the given listings; ignores null prices. */
function cheapestActivePriceCents(listings: Listing[]): number | null {
  let best: number | null = null
  for (const listing of listings) {
    const price = listing.last_known_price_cents
    if (price == null) continue
    if (best == null || price < best) best = price
  }
  return best
}

export interface ListingComparisonHints {
  isBestPrice: boolean
  priceDeltaVsBestCents: number | null
}

/** Best-price highlight and delta labels for a listing within an active set. */
export function listingComparisonHints(
  listing: Listing,
  listings: Listing[],
): ListingComparisonHints {
  if (listings.length < 2) {
    return { isBestPrice: false, priceDeltaVsBestCents: null }
  }

  const bestPriceCents = cheapestActivePriceCents(listings)
  const price = listing.last_known_price_cents
  if (bestPriceCents == null || price == null) {
    return { isBestPrice: false, priceDeltaVsBestCents: null }
  }

  const delta = price - bestPriceCents
  return {
    isBestPrice: delta === 0,
    priceDeltaVsBestCents: delta > 0 ? delta : null,
  }
}

export function needsReviewListings(listings: Listing[]): Listing[] {
  return listings.filter((listing) => listing.review_status === 'needs_review')
}

export function normalizeVariants(
  raw: AvailableVariant[] | null | undefined,
): VariantOption[] {
  if (!raw?.length) return []

  return raw.map((variant) => {
    const attributes: Record<string, string> = {}
    for (const attr of variant.attributes ?? []) {
      const key = attr.attribute_name.toLowerCase()
      attributes[key] = attr.attribute_value
    }
    const label = (variant.attributes ?? [])
      .map((attr) => attr.attribute_value)
      .join(' · ')
    return { attributes, label: label || 'Default' }
  })
}

export function primaryListing(product: ProductDetail): Listing | undefined {
  return product.listings.find((listing) => listing.is_primary) ?? product.listings[0]
}
