import { expect, test } from '@playwright/test'
import { devLogin } from './helpers/auth'

const API_BASE = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000'

test.describe.configure({ mode: 'serial' })

test.describe('search-based product add', () => {
  let productId: string | null = null

  test.beforeEach(async ({ page }) => {
    await devLogin(page)
  })

  test.afterEach(async ({ request }) => {
    if (!productId) return
    await request.delete(`${API_BASE}/api/products/${productId}`).catch(() => undefined)
    productId = null
  })

  test('opens via ⌘K, searches a fixture query, and tracks a result', async ({ page }) => {
    // Header trigger should be visible.
    await expect(page.getByRole('button', { name: /open search/i }).first()).toBeVisible()

    // Open via keyboard shortcut.
    await page.keyboard.press('Meta+k')

    const input = page.getByPlaceholder(/search any product/i)
    await expect(input).toBeVisible()
    await expect(page.getByTestId('search-idle')).toBeVisible()

    // Run a fixture-backed query.
    await input.fill('Nintendo Switch 2')
    await page.getByRole('button', { name: /^search$/i }).click()

    await expect(page.getByTestId('search-results')).toBeVisible({ timeout: 10_000 })
    const rows = page.getByTestId('search-result-row')
    await expect(rows.first()).toBeVisible()
    const rowCount = await rows.count()
    expect(rowCount).toBeGreaterThanOrEqual(1)

    // Track the first result.
    const firstTrack = page.getByTestId('track-button').first()
    await firstTrack.click()

    // Navigation hands off to the product detail page; URL changes.
    await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/, { timeout: 20_000 })
    productId = page.url().split('/').pop() ?? null
    expect(productId).toBeTruthy()

    // The auto-categorization shimmer from PR #47 should appear on the detail page.
    await expect(page.getByTestId('category-thinking')).toBeVisible({ timeout: 5_000 })
  })

  test('empty query shows fallback to URL add', async ({ page }) => {
    await page.keyboard.press('Meta+k')
    const input = page.getByPlaceholder(/search any product/i)
    await input.fill('this query has no fixture results for it zzz')
    await page.getByRole('button', { name: /^search$/i }).click()

    await expect(page.getByTestId('search-empty')).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: /add by url/i }).click()
    await expect(page.getByLabel(/product url/i)).toBeVisible({ timeout: 5_000 })
  })
})
