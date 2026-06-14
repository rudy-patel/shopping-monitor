import { useState } from 'react'
import { Link } from 'react-router-dom'
import { RotateCcw, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TrendChip } from '@/components/products/TrendChip'
import { DeleteProductDialog } from '@/components/products/DeleteProductDialog'
import { useRestoreProduct } from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { formatRelativeTime, retailerLabel } from '@/lib/format'
import type { ProductSummary } from '@/lib/products'
import { categoryLabel } from '@/lib/categories'

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
        {product.image_url ? (
          <img
            src={product.image_url}
            alt=""
            className="h-16 w-16 shrink-0 rounded-md border border-border object-cover"
          />
        ) : (
          <div className="h-16 w-16 shrink-0 rounded-md border border-border bg-muted" />
        )}

        <div className="min-w-0 flex-1">
          <Link
            to={`/products/${product.id}`}
            className="font-medium tracking-tight hover:underline"
          >
            {product.title}
          </Link>
          {product.brand ? (
            <p className="text-sm text-muted-foreground">{product.brand}</p>
          ) : null}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <span>{formatPriceCents(product.best_price_cents)}</span>
            <TrendChip trend={product.trend} />
            <span className="text-muted-foreground">{categoryLabel(product.category)}</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {retailerLabel(product.best_retailer_slug)} · Archived{' '}
            {formatRelativeTime(product.updated_at)}
          </p>
        </div>

        <div className="flex shrink-0 gap-2">
          <Button
            variant="default"
            size="sm"
            disabled={restore.isPending}
            onClick={() => restore.mutate()}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Restore
          </Button>
          <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)}>
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
