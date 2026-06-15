import type { TrendChip as TrendChipType } from '@/lib/products'
import { cn } from '@/lib/utils'

interface TrendChipProps {
  trend: TrendChipType
  className?: string
}

const DIRECTION_PREFIX: Record<TrendChipType['direction'], string> = {
  down: '↓',
  same: '→',
  up: '↑',
}

const DIRECTION_STYLES: Record<TrendChipType['direction'], string> = {
  down: 'bg-trend-down-muted text-trend-down',
  same: 'bg-trend-same-muted text-trend-same',
  up: 'bg-trend-up-muted text-trend-up',
}

/** Subtle price text tint paired with the trend chip on product rows. */
export function trendPriceClass(direction: TrendChipType['direction']): string {
  return {
    down: 'text-trend-down',
    same: 'text-trend-same',
    up: 'text-trend-up',
  }[direction]
}

export function TrendChip({ trend, className }: TrendChipProps) {
  const prefix = DIRECTION_PREFIX[trend.direction]
  const accessibleLabel = `${prefix} ${trend.label}`

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs',
        DIRECTION_STYLES[trend.direction],
        className,
      )}
      aria-label={accessibleLabel}
    >
      {accessibleLabel}
    </span>
  )
}
