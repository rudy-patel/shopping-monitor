import {
  activeListings,
  isProductListQueryKey,
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
})

describe('product query keys', () => {
  it('distinguishes list caches from detail caches', () => {
    expect(isProductListQueryKey(productsQueryKey({ status: 'active' }))).toBe(true)
    expect(isProductListQueryKey(productsQueryKey({ status: 'archived' }))).toBe(true)
    expect(isProductListQueryKey(productQueryKey('product-id'))).toBe(false)
    expect(isProductListQueryKey(['products'])).toBe(false)
  })
})
