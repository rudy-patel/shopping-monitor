import { useParams } from 'react-router-dom'
import { Skeleton } from '@/components/ui/skeleton'

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Product Detail</h1>
      <p className="mb-8 text-muted-foreground">
        View listings, price history, and notification settings for this item.
      </p>
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">
        Product {id} — coming in T2.6
      </p>
    </div>
  )
}
