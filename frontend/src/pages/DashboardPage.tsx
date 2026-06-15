import { Link } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { CategorySection } from '@/components/products/CategorySection'
import { EmptyState } from '@/components/products/EmptyState'
import { ProductListRow } from '@/components/products/ProductListRow'
import { ProductListRowSkeleton } from '@/components/products/ProductListRowSkeleton'
import { useProducts } from '@/hooks/useProducts'
import { CATEGORY_ORDER, groupByCategory } from '@/lib/categories'
import type { ProductSummary } from '@/lib/products'

export function DashboardPage() {
  const { data: products = [] as ProductSummary[], isLoading, isError } = useProducts({ status: 'active' })
  const grouped = groupByCategory<ProductSummary>(products)
  const hasProducts = products.length > 0

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6 md:py-8">
      <div className="mb-6 flex items-end justify-between gap-4 md:mb-8">
        <div>
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Your list</h1>
          <p className="text-sm text-muted-foreground md:text-base">
            Products grouped by category.
          </p>
        </div>
        <div className="hidden flex-wrap items-center gap-3 sm:flex">
          <Link to="/list" className="text-sm underline-offset-4 hover:underline">
            All products
          </Link>
          <Link to="/history" className="text-sm underline-offset-4 hover:underline">
            Archived
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <ProductListRowSkeleton />
          <ProductListRowSkeleton />
          <ProductListRowSkeleton />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-muted-foreground">Could not load products.</p>
      ) : null}

      {!isLoading && !isError && !hasProducts ? (
        <EmptyState
          title="No products yet"
          description="Tap Add to paste your first product URL."
        />
      ) : null}

      {!isLoading && !isError && hasProducts ? (
        <div className="space-y-8 md:space-y-10">
          {CATEGORY_ORDER.map((category) => {
            const items: ProductSummary[] = grouped.get(category) ?? []
            if (items.length === 0) return null
            return (
              <CategorySection key={category} category={category} count={items.length}>
                <AnimatePresence initial={false}>
                  {items.map((product) => (
                    <ProductListRow key={product.id} product={product} />
                  ))}
                </AnimatePresence>
              </CategorySection>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
