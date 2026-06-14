import { Link } from 'react-router-dom'
import { CategorySection } from '@/components/products/CategorySection'
import { EmptyState } from '@/components/products/EmptyState'
import { ProductCard } from '@/components/products/ProductCard'
import { ProductCardSkeleton } from '@/components/products/ProductCardSkeleton'
import { useProducts } from '@/hooks/useProducts'
import { CATEGORY_ORDER, groupByCategory } from '@/lib/categories'
import type { ProductSummary } from '@/lib/products'

export function DashboardPage() {
  const { data: products = [] as ProductSummary[], isLoading, isError } = useProducts({ status: 'active' })
  const grouped = groupByCategory<ProductSummary>(products)
  const hasProducts = products.length > 0

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your list</h1>
          <p className="text-muted-foreground">Products grouped by category.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/list" className="text-sm underline-offset-4 hover:underline">
            All products
          </Link>
          <Link to="/history" className="text-sm underline-offset-4 hover:underline">
            Archived products
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <ProductCardSkeleton />
          <ProductCardSkeleton />
          <ProductCardSkeleton />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-muted-foreground">Could not load products.</p>
      ) : null}

      {!isLoading && !isError && !hasProducts ? (
        <EmptyState
          title="No products yet"
          description="Use Add Product in the header to paste your first URL."
        />
      ) : null}

      {!isLoading && !isError && hasProducts ? (
        <div className="space-y-10">
          {CATEGORY_ORDER.map((category) => {
            const items: ProductSummary[] = grouped.get(category) ?? []
            if (items.length === 0) return null
            return (
              <CategorySection key={category} category={category}>
                {items.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </CategorySection>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
