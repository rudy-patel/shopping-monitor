import { cn } from '@/lib/utils'

interface StockBadgeProps {
  inStock: boolean | null
  className?: string
}

function stockLabel(inStock: boolean | null): string {
  if (inStock === true) return 'In stock'
  if (inStock === false) return 'Out of stock'
  return 'Unknown'
}

export function StockBadge({ inStock, className }: StockBadgeProps) {
  const label = stockLabel(inStock)

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border border-border px-2 py-0.5 text-xs text-muted-foreground',
        inStock === true && 'border-foreground/20 bg-muted/50',
        inStock === false && 'border-foreground/30 bg-muted',
        className,
      )}
    >
      {label}
    </span>
  )
}
