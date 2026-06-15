import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Archive, MoreVertical, RefreshCw, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { CategorySortingBadge } from '@/components/products/CategorySortingBadge'
import { DiscoveryIndicator } from '@/components/products/DiscoveryIndicator'
import { TrendChip } from '@/components/products/TrendChip'
import { useArchiveProduct, useRefreshProduct } from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { useJustAddedCategoryThinking } from '@/lib/just-added-product'
import { listItemTransition, useMotionEnabled } from '@/lib/motion'
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
          <Button variant="ghost" size="icon" className="h-11 w-11" aria-label="Product actions">
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

interface ProductListRowProps {
  product: ProductSummary
  compact?: boolean
}

export function ProductListRow({ product, compact = false }: ProductListRowProps) {
  const refresh = useRefreshProduct(product.id)
  const formatPriceCents = useFormatPriceCents()
  const motionEnabled = useMotionEnabled()
  const { isThinking: isCategorySorting } = useJustAddedCategoryThinking(product.id)
  const detailPath =
    product.status === 'needs_input'
      ? `/products/${product.id}/variants`
      : `/products/${product.id}`
  const extraRetailers = extraRetailerCount(product.listing_count)
  const isRefreshing = refresh.isPending

  return (
    <motion.div
      layout={motionEnabled}
      initial={motionEnabled ? { opacity: 0, height: 0 } : false}
      animate={{ opacity: 1, height: 'auto' }}
      exit={motionEnabled ? { opacity: 0, height: 0 } : undefined}
      transition={listItemTransition}
    >
      <div
        className={cn(
          'rounded-lg border border-border bg-background transition-colors hover:border-foreground/30',
          compact ? 'p-3' : 'p-4',
          isRefreshing && 'opacity-80',
        )}
      >
        <div className="flex gap-2 sm:gap-3">
          <Link to={detailPath} className="min-w-0 flex-1 space-y-1">
            <h3 className="truncate font-medium tracking-tight">{product.title}</h3>
            {product.brand ? (
              <p className="truncate text-sm text-muted-foreground">{product.brand}</p>
            ) : null}

            <div className="flex flex-wrap items-center gap-2 pt-1">
              {isRefreshing ? (
                <>
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-5 w-36" />
                </>
              ) : (
                <>
                  <span className="font-medium tabular-nums">
                    {formatPriceCents(product.best_price_cents)}
                  </span>
                  <TrendChip trend={product.trend} />
                </>
              )}
              {product.status === 'needs_input' ? <Badge>Pick variant</Badge> : null}
              {product.needs_review_count > 0 ? (
                <Badge variant="outline">{product.needs_review_count} to review</Badge>
              ) : null}
              {isCategorySorting ? <CategorySortingBadge /> : null}
            </div>

            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span>{retailerLabel(product.best_retailer_slug)}</span>
              {extraRetailers ? <span>{extraRetailers}</span> : null}
              <span>
                Updated {formatRelativeTime(product.last_refresh_at ?? product.last_scraped_at)}
              </span>
              <DiscoveryIndicator status={product.discovery_status} />
            </div>
          </Link>

          <div className="flex shrink-0 items-start gap-1">
            <ProductActionsMenu
              product={product}
              refreshing={isRefreshing}
              onRefresh={() => refresh.mutate()}
            />
            {!compact ? (
              <Button
                variant="outline"
                size="sm"
                className="hidden h-11 sm:inline-flex"
                disabled={isRefreshing}
                onClick={() => refresh.mutate()}
              >
                {isRefreshing ? 'Refreshing…' : 'Refresh'}
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
