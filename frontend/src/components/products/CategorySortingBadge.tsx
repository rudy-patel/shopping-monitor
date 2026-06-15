import { Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useMotionEnabled } from '@/lib/motion'
import { cn } from '@/lib/utils'

interface CategorySortingBadgeProps {
  compact?: boolean
}

export function CategorySortingBadge({ compact = false }: CategorySortingBadgeProps) {
  const motionEnabled = useMotionEnabled()

  return (
    <Badge
      variant="outline"
      className={cn(compact && 'text-[10px]')}
      data-testid="category-sorting-badge"
    >
      <Sparkles
        className={cn('mr-1 h-3 w-3', motionEnabled && 'animate-pulse')}
        aria-hidden
      />
      Sorting…
    </Badge>
  )
}
