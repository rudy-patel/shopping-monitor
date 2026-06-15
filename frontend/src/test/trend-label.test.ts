import { enrichedTrendLabel } from '@/lib/trend'
import { sampleTrend } from './product-fixtures'

describe('enrichedTrendLabel', () => {
  it('keeps the server label when delta_pct is unknown', () => {
    expect(
      enrichedTrendLabel({
        ...sampleTrend,
        direction: 'down',
        delta_pct: null,
        label: 'Down in the last 30 days',
      }),
    ).toBe('↓ Down in the last 30 days')
  })

  it('appends a quiet percent suffix for down and up trends', () => {
    expect(
      enrichedTrendLabel({
        ...sampleTrend,
        direction: 'down',
        delta_pct: -0.08,
        label: 'Down in the last 30 days',
      }),
    ).toBe('↓ Down 8%')

    expect(
      enrichedTrendLabel({
        ...sampleTrend,
        direction: 'up',
        delta_pct: 0.12,
        label: 'Up in the last 30 days',
      }),
    ).toBe('↑ Up 12%')
  })

  it('shows a ±1% suffix for same-direction deadband moves', () => {
    expect(
      enrichedTrendLabel({
        ...sampleTrend,
        direction: 'same',
        delta_pct: 0.005,
        label: 'Same in the last 30 days',
      }),
    ).toBe('→ Same (±1%)')
  })
})
