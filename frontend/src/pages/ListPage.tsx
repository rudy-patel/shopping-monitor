import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { applyListFilters, ListFilters, type ListFilterState } from '@/components/products/ListFilters'
import { EmptyState } from '@/components/products/EmptyState'
import { ProductCard } from '@/components/products/ProductCard'
import { ProductCardSkeleton } from '@/components/products/ProductCardSkeleton'
import { useProducts } from '@/hooks/useProducts'
import type { ProductSummary } from '@/lib/products'

const DEFAULT_FILTERS: ListFilterState = {
  category: 'all',
  retailer: 'all',
  needsReview: false,
}

export function ListPage() {
  const { data: products = [] as ProductSummary[], isLoading, isError } = useProducts({ status: 'active' })
  const [filters, setFilters] = useState<ListFilterState>(DEFAULT_FILTERS)

  const retailers = useMemo(
    () =>
      [...new Set(products.map((product: ProductSummary) => product.best_retailer_slug).filter(Boolean))].sort() as string[],
    [products],
  )

  const filtered = useMemo(
    () => applyListFilters<ProductSummary>(products, filters),
    [products, filters],
  )

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8">
        <Link to="/" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
          Back to dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">All products</h1>
        <p className="text-muted-foreground">Flat list with filters.</p>
      </div>

      <div className="mb-6">
        <ListFilters filters={filters} retailers={retailers} onChange={setFilters} />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <ProductCardSkeleton />
          <ProductCardSkeleton />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-muted-foreground">Could not load products.</p>
      ) : null}

      {!isLoading && !isError && filtered.length === 0 ? (
        <EmptyState
          title="No matching products"
          description="Try changing filters or add a product from the header."
        />
      ) : null}

      {!isLoading && !isError && filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((product) => (
            <ProductCard key={product.id} product={product} compact />
          ))}
        </div>
      ) : null}
    </div>
  )
}
