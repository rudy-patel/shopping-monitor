import { Skeleton } from '@/components/ui/skeleton'

export function ProductListRowSkeleton() {
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="space-y-2">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <div className="flex gap-3 pt-1">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
    </div>
  )
}
