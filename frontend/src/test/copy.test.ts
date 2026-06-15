import { loginTaglines, dashboardQuotes, footerQuips } from '@/lib/copy'

describe('copy arrays', () => {
  it.each([
    ['loginTaglines', loginTaglines],
    ['dashboardQuotes', dashboardQuotes],
    ['footerQuips', footerQuips],
  ] as const)('%s is non-empty and contains only non-empty strings', (_, lines) => {
    expect(lines.length).toBeGreaterThan(0)
    expect(lines.every((l) => typeof l === 'string' && l.length > 0)).toBe(true)
  })
})
