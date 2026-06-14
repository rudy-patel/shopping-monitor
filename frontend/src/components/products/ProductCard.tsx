import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Archive, MoreVertical, RefreshCw, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { DiscoveryIndicator } from '@/components/products/DiscoveryIndicator'
import { TrendChip } from '@/components/products/TrendChip'
import { useArchiveProduct, useRefreshProduct } from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import {
  extraRetailerCount,
  formatRelativeTime,
  retailerLabel,
} from '@/lib/format'
import type { ProductSummary } from '@/lib/products'
import { cn } from '@/lib/utils'
import { DeleteProductDialog } from './DeleteProductDialog'

interface ProductActionsMenuProps {
  product: ProductSummary
  onRefresh?: () => void
  refreshing?: boolean
}

export function ProductActionsMenu({ product, onRefresh, refreshing }: ProductActionsMenuProps) {
  const archive = useArchiveProduct(product.id)
  const [deleteOpen, setDeleteOpen] = useState(false)

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="Product actions">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem disabled={refreshing} onSelect={() => onRefresh?.()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </DropdownMenuItem>
          <DropdownMenuItem disabled={archive.isPending} onSelect={() => archive.mutate()}>
            <Archive className="mr-2 h-4 w-4" />
            Archive
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setDeleteOpen(true)}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <DeleteProductDialog
        productId={product.id}
        productTitle={product.title}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </>
  )
}

interface ProductCardProps {
  product: ProductSummary
  compact?: boolean
}

export function ProductCard({ product, compact = false }: ProductCardProps) {
  const refresh = useRefreshProduct(product.id)
  const formatPriceCents = useFormatPriceCents()
  const detailPath =
    product.status === 'needs_input'
      ? `/products/${product.id}/variants`
      : `/products/${product.id}`
  const extraRetailers = extraRetailerCount(product.listing_count)

  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-background transition-colors hover:border-foreground/30',
        compact ? 'p-3' : 'p-4',
        refresh.isPending && 'opacity-70',
      )}
    >
      <div className="flex gap-4">
        <Link to={detailPath} className="flex min-w-0 flex-1 gap-4">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt=""
              className={cn(
                'shrink-0 rounded-md border border-border object-cover',
                compact ? 'h-14 w-14' : 'h-20 w-20',
              )}
            />
          ) : (
            <div
              className={cn(
                'shrink-0 rounded-md border border-border bg-muted',
                compact ? 'h-14 w-14' : 'h-20 w-20',
              )}
            />
          )}

          <div className="min-w-0 flex-1">
            <h3 className="truncate font-medium tracking-tight">{product.title}</h3>
            {product.brand ? (
              <p className="truncate text-sm text-muted-foreground">{product.brand}</p>
            ) : null}

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="font-medium">{formatPriceCents(product.best_price_cents)}</span>
              <TrendChip trend={product.trend} />
              {product.status === 'needs_input' ? <Badge>Pick variant</Badge> : null}
              {product.needs_review_count > 0 ? (
                <Badge variant="outline">{product.needs_review_count} to review</Badge>
              ) : null}
            </div>

            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span>{retailerLabel(product.best_retailer_slug)}</span>
              {extraRetailers ? <span>{extraRetailers}</span> : null}
              <span>
                Updated {formatRelativeTime(product.last_refresh_at ?? product.last_scraped_at)}
              </span>
              <DiscoveryIndicator status={product.discovery_status} />
            </div>
          </div>
        </Link>

        <div className="flex shrink-0 items-start gap-2">
          <ProductActionsMenu
            product={product}
            refreshing={refresh.isPending}
            onRefresh={() => refresh.mutate()}
          />
          {!compact ? (
            <Button
              variant="outline"
              size="sm"
              className="hidden sm:inline-flex"
              disabled={refresh.isPending}
              onClick={() => refresh.mutate()}
            >
              <RefreshCw className={cn('mr-2 h-4 w-4', refresh.isPending && 'animate-spin')} />
              Refresh
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
