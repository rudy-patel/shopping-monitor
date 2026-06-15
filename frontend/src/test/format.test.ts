import {
  MISSING_PRICE_LABEL,
  formatCadCents,
  retailerLabel,
} from '@/lib/format'

describe('format helpers', () => {
  it('uses a plain hyphen for missing prices', () => {
    expect(formatCadCents(null)).toBe(MISSING_PRICE_LABEL)
    expect(formatCadCents(undefined)).toBe(MISSING_PRICE_LABEL)
    expect(MISSING_PRICE_LABEL).not.toContain('\u2014')
  })

  it('labels generic scraper listings without em dashes', () => {
    expect(retailerLabel('generic')).toBe('Generic scraper (may be unreliable)')
    expect(retailerLabel('generic')).not.toContain('\u2014')
  })
})
