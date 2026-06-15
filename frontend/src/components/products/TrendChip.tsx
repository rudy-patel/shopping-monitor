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
  down: 'bg-muted/80 text-foreground/90',
  same: 'bg-muted text-muted-foreground',
  up: 'border border-foreground/25 bg-background text-foreground',
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
