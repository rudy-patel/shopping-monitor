import { Sparkles } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useMotionEnabled } from '@/lib/motion'
import { cn } from '@/lib/utils'

export function CategoryFieldThinking() {
  const motionEnabled = useMotionEnabled()

  return (
    <div className="grid gap-2" data-testid="category-thinking">
      <p className="text-sm font-medium leading-none">Category</p>
      <div
        className={cn(
          'flex h-10 w-full max-w-xs items-center gap-2 rounded-md border border-input bg-background px-3',
          motionEnabled && 'animate-pulse',
        )}
        aria-busy="true"
      >
        <Sparkles className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
        <Skeleton className="h-4 flex-1" />
      </div>
      <p className="text-xs text-muted-foreground" aria-live="polite">
        Sorting into your list…
      </p>
    </div>
  )
}
