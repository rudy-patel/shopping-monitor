import type { TrendChip } from '@/lib/products'

const DIRECTION_PREFIX: Record<TrendChip['direction'], string> = {
  down: '↓',
  same: '→',
  up: '↑',
}

function formatDeltaMagnitude(deltaPct: number): string {
  const pct = Math.abs(deltaPct * 100)
  if (pct < 1) return '±1%'
  const rounded = Math.round(pct)
  return `${rounded}%`
}

/** Short display label with optional delta suffix for trend chips. */
export function enrichedTrendLabel(trend: TrendChip): string {
  const prefix = DIRECTION_PREFIX[trend.direction]
  const directionWord =
    trend.direction === 'down' ? 'Down' : trend.direction === 'up' ? 'Up' : 'Same'

  if (trend.delta_pct == null) {
    return `${prefix} ${trend.label}`
  }

  const deltaSuffix = formatDeltaMagnitude(trend.delta_pct)
  if (trend.direction === 'same') {
    return `${prefix} Same (${deltaSuffix})`
  }
  return `${prefix} ${directionWord} ${deltaSuffix}`
}
