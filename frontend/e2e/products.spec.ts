import { expect, test } from '@playwright/test'
import { devLogin } from './helpers/auth'

const IN_STOCK_URL = 'https://fixtures.local/bestbuy_ca/in_stock'
const API_BASE = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000'

test.describe.configure({ mode: 'serial' })

test.describe('product vertical slice', () => {
  let productId: string | null = null

  test.beforeEach(async ({ page }) => {
    await devLogin(page)
  })

  test.afterAll(async ({ request }) => {
    if (!productId) return
    await request.delete(`${API_BASE}/api/products/${productId}`).catch(() => undefined)
  })

  test('full fixture-backed lifecycle', async ({ page }) => {
    const productLink = () => page.locator(`a[href="/products/${productId}"]`)
    const archivedRow = () =>
      page.getByRole('main').locator('div.rounded-lg.border', { has: productLink() })

    const openDetailFromDashboard = async () => {
      await productLink().click()
      await expect(page).toHaveURL(new RegExp(`/products/${productId}`))
    }

    await page.getByRole('button', { name: /add product/i }).click()
    await page.getByLabel(/product url/i).fill(IN_STOCK_URL)
    await page.getByRole('button', { name: /^add$/i }).click()

    await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/, { timeout: 15_000 })
    productId = page.url().split('/').pop() ?? null
    expect(productId).toBeTruthy()

    await expect(page.getByTestId('category-thinking')).toBeVisible()
    await expect(page.getByTestId('category-select')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('category-thinking')).toHaveCount(0)

    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/.+/)
    await expect(page.getByText(/best buy canada/i).first()).toBeVisible()
    await expect(page.getByText(/^in stock$/i).first()).toBeVisible()

    const categoryCombobox = page.getByRole('combobox', { name: /category/i })
    const currentCategory = (await categoryCombobox.innerText()).toLowerCase()
    const targetCategory = currentCategory.includes('home') ? 'Clothing' : 'Home'
    await categoryCombobox.click()
    await page.getByRole('option', { name: new RegExp(`^${targetCategory}$`, 'i') }).click()
    await page.keyboard.press('Escape')
    await expect(categoryCombobox).toContainText(new RegExp(targetCategory, 'i'), { timeout: 10_000 })

    const threshold = page.locator('#threshold')
    await threshold.click()
    await threshold.fill('15')
    await threshold.press('Tab')
    await expect(threshold).toHaveValue('15')

    const refreshButton = page.getByRole('button', { name: /^refresh$/i })
    await refreshButton.click()
    await expect(refreshButton).toBeEnabled({ timeout: 30_000 })
    await expect(page.getByText(/best buy canada/i).first()).toBeVisible()
    await expect(page.getByText(/^in stock$/i).first()).toBeVisible()

    await page.getByRole('link', { name: /back to dashboard/i }).click()
    await expect(page).toHaveURL('/', { timeout: 10_000 })
    await expect(productLink()).toBeVisible({ timeout: 15_000 })

    await openDetailFromDashboard()
    await page.getByRole('button', { name: /^archive$/i }).click()
    await expect(page).toHaveURL(new RegExp(`/products/${productId}`), { timeout: 10_000 })
    await expect(page.getByText(/product archived/i)).toBeVisible({ timeout: 5_000 })
    await expect(page.getByText(/this product is archived/i)).toBeVisible()

    await page.goto('/')
    await expect(productLink()).toHaveCount(0)

    await page.goto('/history')
    await archivedRow().getByRole('button', { name: /^restore$/i }).click()

    await page.goto('/')
    await expect(productLink()).toBeVisible({ timeout: 15_000 })

    await openDetailFromDashboard()
    await page.getByRole('button', { name: /^delete$/i }).click()
    const dialog = page.getByRole('alertdialog')
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: /^delete$/i }).click()

    await expect(page).toHaveURL('/', { timeout: 10_000 })
    await expect(productLink()).toHaveCount(0)

    await page.goto('/history')
    await expect(archivedRow()).toHaveCount(0)

    productId = null
  })
})
