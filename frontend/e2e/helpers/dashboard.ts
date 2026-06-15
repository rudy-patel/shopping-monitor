import { expect, type Page } from '@playwright/test'

function isActiveProductsResponse(response: { url: () => string; request: () => { method: () => string } }) {
  const url = response.url()
  return (
    url.includes('/api/products') &&
    url.includes('status=active') &&
    response.request().method() === 'GET'
  )
}

/** Wait for the dashboard active-products fetch to finish (call before navigation when possible). */
export function waitForActiveProducts(page: Page) {
  return page.waitForResponse(
    (response) => isActiveProductsResponse(response) && response.ok(),
    { timeout: 30_000 },
  )
}

/** Navigate to `/` and wait until the grouped dashboard has loaded products. */
export async function gotoDashboard(page: Page) {
  const productsLoaded = waitForActiveProducts(page)
  await page.goto('/')
  await productsLoaded
  await expect(page.getByText('Could not load products.')).not.toBeVisible()
  await expect(page.getByRole('heading', { name: 'Wishlist', exact: true })).toBeVisible()
}

/** Return to dashboard via a caller-provided action (link click, etc.). */
export async function returnToDashboard(page: Page, action: () => Promise<void>) {
  const productsLoaded = waitForActiveProducts(page)
  await action()
  await expect(page).toHaveURL('/', { timeout: 15_000 })
  await productsLoaded
  await expect(page.getByText('Could not load products.')).not.toBeVisible()
}

/** Retry until a dashboard product link is visible (handles transient Supabase errors in CI). */
export async function expectDashboardProductLink(page: Page, name: string | RegExp) {
  const link = page.getByRole('link', { name })

  await expect(async () => {
    if (await page.getByText('Could not load products.').isVisible()) {
      const reloadProducts = waitForActiveProducts(page)
      await page.reload()
      await reloadProducts
    }
    await expect(link).toBeVisible({ timeout: 5_000 })
  }).toPass({ timeout: 45_000 })
}
