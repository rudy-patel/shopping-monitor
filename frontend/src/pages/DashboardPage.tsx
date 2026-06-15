import { useState } from 'react'
import { Link } from 'react-router-dom'
import { DashboardCategoryList } from '@/components/products/DashboardCategoryList'
import { EmptyState } from '@/components/products/EmptyState'
import { ProductListRowSkeleton } from '@/components/products/ProductListRowSkeleton'
import { RotatingCopy } from '@/components/layout/RotatingCopy'
import { Button } from '@/components/ui/button'
import { useProducts } from '@/hooks/useProducts'
import type { ProductSummary } from '@/lib/products'
import { dashboardQuotes, DASHBOARD_TITLE } from '@/lib/copy'

export function DashboardPage() {
  const { data: products = [] as ProductSummary[], isLoading, isError } = useProducts({
    status: 'active',
  })
  const [editMode, setEditMode] = useState(false)
  const hasProducts = products.length > 0

  return (
    <div className="container mx-auto max-w-5xl px-4 py-5 md:py-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 md:mb-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">{DASHBOARD_TITLE}</h1>
          <p className="text-sm text-muted-foreground md:text-base">
            Products grouped by category.
          </p>
          {hasProducts && (
            <p className="mt-1 text-xs italic text-muted-foreground" aria-hidden="true">
              <RotatingCopy lines={dashboardQuotes} interval={6000} />
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant={editMode ? 'default' : 'outline'}
            size="sm"
            className="h-8 px-3"
            onClick={() => setEditMode((current) => !current)}
          >
            {editMode ? 'Done' : 'Edit order'}
          </Button>
          <Link to="/list" className="hidden text-sm underline-offset-4 hover:underline sm:inline">
            All products
          </Link>
          <Link
            to="/history"
            className="hidden text-sm underline-offset-4 hover:underline sm:inline"
          >
            Archived
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <ProductListRowSkeleton />
          <ProductListRowSkeleton />
          <ProductListRowSkeleton />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-muted-foreground">Could not load products.</p>
      ) : null}

      {!isLoading && !isError && !hasProducts ? (
        <div className="mb-8">
          <EmptyState
            showBrandMark
            title="No products yet"
            description="Tap Add to paste your first product URL."
          />
        </div>
      ) : null}

      {!isLoading && !isError ? (
        <DashboardCategoryList products={products} editMode={editMode} />
      ) : null}
    </div>
  )
}
