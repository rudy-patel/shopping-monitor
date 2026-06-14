import { Skeleton } from '@/components/ui/skeleton'

export function HistoryPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">History</h1>
      <p className="mb-8 text-muted-foreground">
        Review price changes and activity over time.
      </p>
      <div className="space-y-3">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">Coming in T3.3</p>
    </div>
  )
}
