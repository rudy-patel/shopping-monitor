import { Skeleton } from '@/components/ui/skeleton'

export function ListPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">All Products</h1>
      <p className="mb-8 text-muted-foreground">
        Browse your full wishlist in a flat list view.
      </p>
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">Coming in T2.6</p>
    </div>
  )
}
