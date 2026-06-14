import { describe, expect, it } from 'vitest'
import {
  productDetailRefetchInterval,
  productListRefetchInterval,
} from '@/hooks/useProducts'
import type { ProductDetail, ProductSummary } from '@/lib/products'

function summary(
  overrides: Partial<ProductSummary> = {},
): ProductSummary {
  return {
    id: 'product-id',
    title: 'Product',
    brand: null,
    image_url: null,
    category: 'tech',
    category_source: 'heuristic',
    status: 'active',
    notification_threshold_pct: null,
    notifications_enabled: true,
    discovery_status: 'complete',
    last_refresh_at: null,
    last_user_interaction_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    best_price_cents: 1000,
    best_retailer_slug: 'bestbuy_ca',
    trend: {
      direction: 'same',
      delta_pct: null,
      days_of_data: 0,
      label: 'Same in the last 30 days',
    },
    listing_count: 1,
    effective_threshold_pct: 10,
    last_scraped_at: null,
    needs_review_count: 0,
    ...overrides,
  }
}

describe('product polling intervals', () => {
  it('polls product detail every 3s while discovery is pending or running', () => {
    const pending: ProductDetail = {
      ...summary({ discovery_status: 'pending' }),
      listings: [],
    }
    const running: ProductDetail = {
      ...summary({ discovery_status: 'running' }),
      listings: [],
    }
    const complete: ProductDetail = {
      ...summary({ discovery_status: 'complete' }),
      listings: [],
    }

    expect(productDetailRefetchInterval(pending)).toBe(3000)
    expect(productDetailRefetchInterval(running)).toBe(3000)
    expect(productDetailRefetchInterval(complete)).toBe(false)
    expect(productDetailRefetchInterval(undefined)).toBe(false)
  })

  it('polls product lists every 5s when any product discovery is in flight', () => {
    const items = [
      summary({ discovery_status: 'complete' }),
      summary({ id: 'other', discovery_status: 'pending' }),
    ]

    expect(productListRefetchInterval(items)).toBe(5000)
    expect(productListRefetchInterval([summary({ discovery_status: 'complete' })])).toBe(
      false,
    )
    expect(productListRefetchInterval(undefined)).toBe(false)
  })
})
