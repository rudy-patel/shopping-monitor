import { baselineMaxCentsFromHistory, effectiveThresholdPct, thresholdTriggerCents } from '@/lib/pricing'

describe('pricing helpers', () => {
  it('uses the max observed price as the notification baseline', () => {
    expect(
      baselineMaxCentsFromHistory(
        [
          { observed_on: '2026-06-01', price_cents: 28999 },
          { observed_on: '2026-06-14', price_cents: 27999 },
        ],
        27999,
      ),
    ).toBe(28999)
  })

  it('falls back to the current best price when history is empty', () => {
    expect(baselineMaxCentsFromHistory([], 27999)).toBe(27999)
  })

  it('computes the threshold trigger from baseline and percent off', () => {
    expect(thresholdTriggerCents(27999, 20)).toBe(22399)
  })

  it('resolves the effective threshold from draft, saved value, or default', () => {
    expect(effectiveThresholdPct('25', 10, 20)).toBe(25)
    expect(effectiveThresholdPct('', 10, 20)).toBe(10)
    expect(effectiveThresholdPct('', null, 20)).toBe(20)
    expect(effectiveThresholdPct('abc', null, 20)).toBe(20)
  })
})
