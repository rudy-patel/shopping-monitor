import { expect, test } from '@playwright/test'
import { devLogin } from './helpers/auth'

test.describe('settings', () => {
  test.beforeEach(async ({ page }) => {
    await devLogin(page)
  })

  test('theme persists across reload', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForResponse(
      (response) =>
        response.url().includes('/api/profile') &&
        response.request().method() === 'GET' &&
        response.ok(),
    )
    await expect(page.getByRole('heading', { level: 1, name: /^settings$/i })).toBeVisible()

    const darkMode = page.getByRole('switch', { name: /dark mode/i })
    await expect(darkMode).toBeVisible()

    if (await darkMode.isChecked()) {
      await darkMode.click()
      await page.waitForResponse(
        (response) =>
          response.url().includes('/api/profile') &&
          response.request().method() === 'PATCH' &&
          response.request().postData()?.includes('"theme":"light"') &&
          response.ok(),
      )
      await expect(darkMode).not.toBeChecked()
    }

    const patchPromise = page.waitForResponse(
      (response) =>
        response.url().includes('/api/profile') &&
        response.request().method() === 'PATCH' &&
        response.request().postData()?.includes('"theme":"dark"') &&
        response.ok(),
    )

    await darkMode.click()
    await patchPromise
    await expect(darkMode).toBeChecked()
    await expect(page.locator('html')).toHaveClass(/dark/)

    await page.reload()
    await page.waitForResponse(
      (response) =>
        response.url().includes('/api/profile') &&
        response.request().method() === 'GET' &&
        response.ok(),
    )
    await expect(page.getByRole('heading', { level: 1, name: /^settings$/i })).toBeVisible()
    await expect(page.getByRole('switch', { name: /dark mode/i })).toBeChecked()
    await expect(page.locator('html')).toHaveClass(/dark/)
  })
})
