import type { Page } from '@playwright/test'

export async function devLogin(page: Page) {
  await page.goto('/login')
  const devButton = page.getByRole('button', { name: /dev login/i })
  if (await devButton.isVisible().catch(() => false)) {
    await devButton.click()
  } else {
    await page.evaluate(() => {
      localStorage.setItem('shopping-monitor-dev-auth', 'true')
    })
    await page.goto('/')
  }
  await page.waitForURL((url) => !url.pathname.includes('/login'))
}
