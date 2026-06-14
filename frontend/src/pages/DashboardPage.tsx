import { Skeleton } from '@/components/ui/skeleton'

export function DashboardPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Dashboard</h1>
      <p className="mb-8 text-muted-foreground">
        Track everything you want in one place.
      </p>
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">Coming in T2.6</p>
    </div>
  )
}
