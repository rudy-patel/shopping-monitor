import { Skeleton } from '@/components/ui/skeleton'

export function ProductListRowSkeleton() {
  return (
    <div className="rounded-md border border-border px-3 py-2.5">
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1 space-y-1">
          <Skeleton className="h-4 w-3/4" />
          <div className="flex gap-2">
            <Skeleton className="h-3.5 w-14" />
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="hidden h-3.5 w-24 sm:block" />
          </div>
        </div>
        <Skeleton className="h-8 w-8 shrink-0 rounded-md" />
      </div>
    </div>
  )
}
