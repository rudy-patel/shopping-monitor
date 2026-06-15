import {
  activeListings,
  cheapestActivePriceCents,
  isCheapestListing,
  isProductListQueryKey,
  listingPriceDeltaVsBest,
  needsReviewListings,
  productQueryKey,
  productsQueryKey,
} from '@/lib/products'
import { makeNeedsReviewListing, makeProductDetail } from './product-fixtures'

describe('listing partition helpers', () => {
  const primary = makeProductDetail().listings[0]
  const review = makeNeedsReviewListing()
  const rejected = makeNeedsReviewListing({
    id: 'rejected-1',
    review_status: 'rejected',
  })
  const autoAdded = makeNeedsReviewListing({
    id: 'auto-1',
    review_status: 'auto_added',
    last_known_price_cents: 5000,
  })

  it('needsReviewListings returns only needs_review rows', () => {
    const listings = [primary, review, rejected, autoAdded]
    expect(needsReviewListings(listings)).toEqual([review])
  })

  it('activeListings excludes needs_review and rejected, sorted by price', () => {
    const expensive = { ...autoAdded, last_known_price_cents: 15000 }
    const listings = [primary, review, rejected, expensive, autoAdded]
    expect(activeListings(listings).map((row) => row.id)).toEqual([
      autoAdded.id,
      primary.id,
      expensive.id,
    ])
  })

  it('comparison helpers derive best price and deltas', () => {
    const expensive = { ...autoAdded, last_known_price_cents: 15000 }
    const active = activeListings([primary, expensive, autoAdded])
    const best = cheapestActivePriceCents(active)
    expect(best).toBe(5000)
    expect(isCheapestListing(autoAdded, best, active.length)).toBe(true)
    expect(isCheapestListing(primary, best, active.length)).toBe(false)
    expect(listingPriceDeltaVsBest(primary, best)).toBe(7999)
    expect(listingPriceDeltaVsBest(autoAdded, best)).toBeNull()
    expect(isCheapestListing(primary, best, 1)).toBe(false)
  })
})

describe('product query keys', () => {
  it('distinguishes list caches from detail caches', () => {
    expect(isProductListQueryKey(productsQueryKey({ status: 'active' }))).toBe(true)
    expect(isProductListQueryKey(productsQueryKey({ status: 'archived' }))).toBe(true)
    expect(isProductListQueryKey(productQueryKey('product-id'))).toBe(false)
    expect(isProductListQueryKey(['products'])).toBe(false)
  })
})
