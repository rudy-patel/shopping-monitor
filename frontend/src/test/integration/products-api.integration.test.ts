import { describe, expect, it } from 'vitest'
import { getApiUrl } from '@/lib/env'
import { IN_STOCK_URL } from '../product-fixtures'

const integrationEnabled = process.env.VITE_INTEGRATION === '1'

describe.skipIf(!integrationEnabled)(
  'products API integration',
  () => {
    let productId: string | null = null

    it('creates, lists, and deletes a fixture-backed product', async () => {
      const base = getApiUrl()

      const createResponse = await fetch(`${base}/api/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: IN_STOCK_URL }),
      })
      expect(createResponse.status).toBe(201)
      const created = (await createResponse.json()) as { id: string }
      productId = created.id

      const listResponse = await fetch(`${base}/api/products`)
      expect(listResponse.status).toBe(200)
      const list = (await listResponse.json()) as { id: string }[]
      expect(list.some((row) => row.id === productId)).toBe(true)

      const deleteResponse = await fetch(`${base}/api/products/${productId}`, {
        method: 'DELETE',
      })
      expect(deleteResponse.status).toBe(204)
      productId = null
    })

    it('cleans up created product if prior step failed', async () => {
      if (!productId) return
      const base = getApiUrl()
      await fetch(`${base}/api/products/${productId}`, { method: 'DELETE' })
      productId = null
    })
  },
  30_000,
)

if (!integrationEnabled) {
  console.info('Skipping products API integration tests (set VITE_INTEGRATION=1 to run).')
}
