import { useState } from 'react'
import { Link } from 'react-router-dom'
import { RotateCcw, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TrendChip, trendPriceClass } from '@/components/products/TrendChip'
import { DeleteProductDialog } from '@/components/products/DeleteProductDialog'
import { useRestoreProduct } from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { RetailerIdentity } from '@/components/retailers/RetailerLogo'
import { formatRelativeTime } from '@/lib/format'
import type { ProductSummary } from '@/lib/products'
import { categoryLabel } from '@/lib/categories'
import { cn } from '@/lib/utils'

interface ArchivedProductRowProps {
  product: ProductSummary
}

export function ArchivedProductRow({ product }: ArchivedProductRowProps) {
  const formatPriceCents = useFormatPriceCents()
  const restore = useRestoreProduct(product.id)
  const [deleteOpen, setDeleteOpen] = useState(false)

  return (
    <>
      <div className="flex flex-col gap-4 rounded-lg border border-border p-4 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1 space-y-1">
          <Link
            to={`/products/${product.id}`}
            className="font-medium tracking-tight hover:underline"
          >
            {product.title}
          </Link>
          {product.brand ? (
            <p className="text-sm text-muted-foreground">{product.brand}</p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span
              className={cn('tabular-nums', trendPriceClass(product.trend.direction))}
            >
              {formatPriceCents(product.best_price_cents)}
            </span>
            <TrendChip trend={product.trend} />
            <span className="text-muted-foreground">{categoryLabel(product.category)}</span>
          </div>
          <p className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
            <RetailerIdentity slug={product.best_retailer_slug} size="xs" />
            <span>· Archived {formatRelativeTime(product.updated_at)}</span>
          </p>
        </div>

        <div className="flex shrink-0 gap-2">
          <Button
            variant="default"
            size="sm"
            className="h-11"
            disabled={restore.isPending}
            onClick={() => restore.mutate()}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Restore
          </Button>
          <Button variant="outline" size="sm" className="h-11" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <DeleteProductDialog
        productId={product.id}
        productTitle={product.title}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        redirectTo="/history"
      />
    </>
  )
}
