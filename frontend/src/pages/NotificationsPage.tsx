import { Skeleton } from '@/components/ui/skeleton'

export function NotificationsPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Notifications</h1>
      <p className="mb-8 text-muted-foreground">
        Price drops, revisit prompts, and other updates appear here.
      </p>
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">Coming in T3.3</p>
    </div>
  )
}
