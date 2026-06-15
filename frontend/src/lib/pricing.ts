import type { PriceHistoryPoint } from '@/lib/products'

/** MAX of daily-min prices in history; falls back to current best when empty. */
export function baselineMaxCentsFromHistory(
  history: PriceHistoryPoint[],
  fallbackCents: number | null,
): number | null {
  if (history.length > 0) {
    return Math.max(...history.map((point) => point.price_cents))
  }
  return fallbackCents
}

/** Price-drop alert fires when current falls at or below this level (PRD §7.4). */
export function thresholdTriggerCents(
  baselineCents: number,
  thresholdPct: number,
): number {
  return Math.round(baselineCents * (1 - thresholdPct / 100))
}

/** Resolve the threshold % shown in the UI from draft input, saved value, or profile default. */
export function effectiveThresholdPct(
  draft: string,
  value: number | null,
  effectiveDefault: number,
): number {
  const trimmed = draft.trim()
  if (!trimmed) return value ?? effectiveDefault
  const parsed = Number(trimmed)
  if (Number.isInteger(parsed) && parsed >= 1 && parsed <= 95) return parsed
  return value ?? effectiveDefault
}
