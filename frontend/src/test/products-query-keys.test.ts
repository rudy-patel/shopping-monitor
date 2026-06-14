import { isProductListQueryKey, productQueryKey, productsQueryKey } from '@/lib/products'

describe('product query keys', () => {
  it('distinguishes list caches from detail caches', () => {
    expect(isProductListQueryKey(productsQueryKey({ status: 'active' }))).toBe(true)
    expect(isProductListQueryKey(productsQueryKey({ status: 'archived' }))).toBe(true)
    expect(isProductListQueryKey(productQueryKey('product-id'))).toBe(false)
    expect(isProductListQueryKey(['products'])).toBe(false)
  })
})
