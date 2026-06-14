import type { ProductDetail, ProductSummary, TrendChip } from '@/lib/products'

export const sampleTrend: TrendChip = {
  direction: 'down',
  delta_pct: 5,
  days_of_data: 10,
  label: 'Down in the last 30 days',
}

export function makeProductSummary(overrides: Partial<ProductSummary> = {}): ProductSummary {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    title: 'Sample Product',
    brand: 'Sample Brand',
    image_url: null,
    category: 'tech',
    category_source: 'heuristic',
    status: 'active',
    notification_threshold_pct: null,
    notifications_enabled: true,
    discovery_status: 'complete',
    last_refresh_at: '2026-06-13T12:00:00.000Z',
    last_user_interaction_at: null,
    created_at: '2026-06-13T10:00:00.000Z',
    updated_at: '2026-06-13T12:00:00.000Z',
    best_price_cents: 12999,
    best_retailer_slug: 'bestbuy_ca',
    trend: sampleTrend,
    listing_count: 1,
    effective_threshold_pct: 20,
    last_scraped_at: '2026-06-13T12:00:00.000Z',
    needs_review_count: 0,
    ...overrides,
  }
}

export function makeProductDetail(overrides: Partial<ProductDetail> = {}): ProductDetail {
  const summary = makeProductSummary(overrides)
  return {
    ...summary,
    listings: overrides.listings ?? [
      {
        id: '22222222-2222-2222-2222-222222222222',
        retailer_slug: 'bestbuy_ca',
        url: 'https://fixtures.local/bestbuy_ca/in_stock',
        variant_attributes: {},
        available_variants: null,
        is_primary: true,
        review_status: 'accepted',
        last_known_price_cents: 12999,
        is_in_stock: true,
        last_scraped_at: '2026-06-13T12:00:00.000Z',
        scrape_status: 'ok',
        match_confidence: null,
      },
    ],
    ...overrides,
  }
}

export const IN_STOCK_URL = 'https://fixtures.local/bestbuy_ca/in_stock'
export const MULTI_VARIANT_URL = 'https://fixtures.local/bestbuy_ca/multi_variant'
