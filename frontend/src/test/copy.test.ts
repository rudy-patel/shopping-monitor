import { readFileSync } from 'node:fs'
import path from 'node:path'
import { loginTaglines, dashboardQuotes, footerQuips, DASHBOARD_TITLE, SITE_DESCRIPTION, SITE_NAME } from '@/lib/copy'

const EM_DASH = '\u2014'

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

  it('avoids em dashes in user-facing copy', () => {
    const strings = [
      SITE_DESCRIPTION,
      ...loginTaglines,
      ...dashboardQuotes,
      ...footerQuips,
    ]
    for (const line of strings) {
      expect(line).not.toContain(EM_DASH)
    }
  })
})
