import { applyListFilters } from '@/components/products/ListFilters'
import { makeProductSummary } from './product-fixtures'

const products = [
  makeProductSummary({
    id: '1',
    title: 'Tech at Best Buy',
    category: 'tech',
    best_retailer_slug: 'bestbuy_ca',
    needs_review_count: 0,
  }),
  makeProductSummary({
    id: '2',
    title: 'Home Generic',
    category: 'home',
    best_retailer_slug: 'generic',
    needs_review_count: 2,
  }),
  makeProductSummary({
    id: '3',
    title: 'Shoe Item',
    category: 'shoes',
    best_retailer_slug: 'bestbuy_ca',
    needs_review_count: 0,
  }),
]

describe('applyListFilters', () => {
  it('filters by category, retailer, and needs review', () => {
    const needsReviewOnly = applyListFilters(products, {
      category: 'all',
      retailer: 'all',
      needsReview: true,
    })
    expect(needsReviewOnly.map((p) => p.title)).toEqual(['Home Generic'])

    const techOnly = applyListFilters(products, {
      category: 'tech',
      retailer: 'all',
      needsReview: false,
    })
    expect(techOnly.map((p) => p.title)).toEqual(['Tech at Best Buy'])

    const genericOnly = applyListFilters(products, {
      category: 'all',
      retailer: 'generic',
      needsReview: false,
    })
    expect(genericOnly.map((p) => p.title)).toEqual(['Home Generic'])
  })
})
