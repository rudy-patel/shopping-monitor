import { expect, test } from '@playwright/test'
import { devLogin } from './helpers/auth'

const IN_STOCK_URL = 'https://fixtures.local/bestbuy_ca/in_stock'
const API_BASE = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000'

test.describe('product happy path', () => {
  let productId: string | null = null

  test.beforeEach(async ({ page }) => {
    await devLogin(page)
  })

  test.afterAll(async ({ request }) => {
    if (!productId) return
    await request.delete(`${API_BASE}/api/products/${productId}`).catch(() => undefined)
  })

  test('add, archive to history, restore back to dashboard', async ({ page, request }) => {
    await page.getByRole('button', { name: /add product/i }).click()
    await page.getByLabel(/product url/i).fill(IN_STOCK_URL)
    await page.getByRole('button', { name: /^add$/i }).click()

    await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/, { timeout: 15_000 })
    productId = page.url().split('/').pop() ?? null
    expect(productId).toBeTruthy()

    const productTitle = await page.getByRole('heading', { level: 1 }).innerText()

    await page.goto('/')
    await expect(page.getByText(productTitle).first()).toBeVisible({ timeout: 15_000 })

    await page.getByRole('link', { name: new RegExp(productTitle, 'i') }).first().click()
    await page.getByRole('button', { name: /^archive$/i }).click()

    await expect(page).toHaveURL('/history', { timeout: 10_000 })
    await expect(page.getByRole('heading', { name: /archived products/i })).toBeVisible()
    await expect(page.getByText(productTitle)).toBeVisible()

    await page.goto('/')
    await expect(page.getByText(productTitle)).toHaveCount(0)

    await page.goto('/history')
    await page.getByRole('button', { name: /^restore$/i }).first().click()

    await page.goto('/')
    await expect(page.getByText(productTitle).first()).toBeVisible({ timeout: 10_000 })

    if (productId) {
      await request.delete(`${API_BASE}/api/products/${productId}`)
      productId = null
    }
  })
})
