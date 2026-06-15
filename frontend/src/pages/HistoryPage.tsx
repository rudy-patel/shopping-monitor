import { Link } from 'react-router-dom'
import { ArchivedProductRow } from '@/components/products/ArchivedProductRow'
import { EmptyState } from '@/components/products/EmptyState'
import { ProductListRowSkeleton } from '@/components/products/ProductListRowSkeleton'
import { useProducts } from '@/hooks/useProducts'
import type { ProductSummary } from '@/lib/products'

export function HistoryPage() {
  const { data: products = [] as ProductSummary[], isLoading, isError } = useProducts({
    status: 'archived',
  })

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <Link to="/" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
        Back to dashboard
      </Link>

      <div className="mt-6 mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Archived</h1>
        <p className="mt-2 text-muted-foreground">
          Products you archived are kept here with their price history. Restore any item to track it
          again.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <ProductListRowSkeleton />
          <ProductListRowSkeleton />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-muted-foreground">Could not load archived products.</p>
      ) : null}

      {!isLoading && !isError && products.length === 0 ? (
        <EmptyState
          title="No archived products"
          description="When you archive something from your list, it will appear here."
        />
      ) : null}

      {!isLoading && !isError && products.length > 0 ? (
        <div className="space-y-3">
          {products.map((product: ProductSummary) => (
            <ArchivedProductRow key={product.id} product={product} />
          ))}
        </div>
      ) : null}
    </div>
  )
}
