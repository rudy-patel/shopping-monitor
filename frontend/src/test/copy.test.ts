import { loginTaglines, dashboardQuotes, footerQuips, DASHBOARD_TITLE, SITE_DESCRIPTION, SITE_NAME } from '@/lib/copy'

describe('copy arrays', () => {
  it.each([
    ['loginTaglines', loginTaglines],
    ['dashboardQuotes', dashboardQuotes],
    ['footerQuips', footerQuips],
  ] as const)('%s is non-empty and contains only non-empty strings', (_, lines) => {
    expect(lines.length).toBeGreaterThan(0)
    expect(lines.every((l) => typeof l === 'string' && l.length > 0)).toBe(true)
  })

  it('exports site branding constants', () => {
    expect(SITE_NAME).toBe('Someday')
    expect(DASHBOARD_TITLE).toBe('Wishlist')
    expect(SITE_DESCRIPTION.length).toBeGreaterThan(10)
  })
})
