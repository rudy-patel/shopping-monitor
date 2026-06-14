import { useParams } from 'react-router-dom'
import { Skeleton } from '@/components/ui/skeleton'

export function VariantPickerPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Choose Variant</h1>
      <p className="mb-8 text-muted-foreground">
        Select the product variant you want to track.
      </p>
      <div className="space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">
        Product {id} — coming in T2.6
      </p>
    </div>
  )
}
