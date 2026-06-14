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

export function TrendChip({ trend, className }: TrendChipProps) {
  const prefix = DIRECTION_PREFIX[trend.direction]
  const accessibleLabel = `${prefix} ${trend.label}`

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground',
        className,
      )}
      aria-label={accessibleLabel}
    >
      {accessibleLabel}
    </span>
  )
}
