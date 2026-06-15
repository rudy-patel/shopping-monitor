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
import { TrendChip, trendPriceClass } from '@/components/products/TrendChip'
import { useArchiveProduct, useRefreshProduct } from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { useJustAddedCategoryThinking } from '@/lib/just-added-product'
import { listItemTransition, useMotionEnabled } from '@/lib/motion'
import { RetailerIdentity } from '@/components/retailers/RetailerLogo'
import {
  extraRetailerCount,
  formatRelativeTime,
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
          <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Product actions">
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
}

export function ProductListRow({ product }: ProductListRowProps) {
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
          'rounded-md border border-border bg-background px-3 py-2.5 transition-colors hover:border-foreground/30',
          isRefreshing && 'opacity-80',
        )}
      >
        <div className="flex items-center gap-1.5 sm:gap-2">
          <Link to={detailPath} className="min-w-0 flex-1">
            <div className="flex min-w-0 items-baseline gap-1.5">
              <h3 className="truncate text-sm font-medium leading-snug tracking-tight">
                {product.title}
              </h3>
              {product.brand ? (
                <>
                  <span className="shrink-0 text-muted-foreground/60" aria-hidden="true">
                    ·
                  </span>
                  <span className="shrink-0 truncate text-xs text-muted-foreground">
                    {product.brand}
                  </span>
                </>
              ) : null}
            </div>

            <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
              {isRefreshing ? (
                <>
                  <Skeleton className="h-4 w-14" />
                  <Skeleton className="h-4 w-24" />
                </>
              ) : (
                <>
                  <span
                    className={cn(
                      'text-sm font-medium tabular-nums leading-none',
                      trendPriceClass(product.trend.direction),
                    )}
                  >
                    {formatPriceCents(product.best_price_cents)}
                  </span>
                  <TrendChip trend={product.trend} compact />
                </>
              )}
              {product.status === 'needs_input' ? (
                <Badge className="px-1.5 py-0 text-xs">Pick variant</Badge>
              ) : null}
              {product.needs_review_count > 0 ? (
                <Badge variant="outline" className="px-1.5 py-0 text-xs">
                  {product.needs_review_count} to review
                </Badge>
              ) : null}
              {isCategorySorting ? <CategorySortingBadge compact /> : null}
              <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs leading-none text-muted-foreground sm:ml-auto">
                <RetailerIdentity slug={product.best_retailer_slug} size="xs" />
                {extraRetailers ? <span>{extraRetailers}</span> : null}
                <span>
                  Updated {formatRelativeTime(product.last_refresh_at ?? product.last_scraped_at)}
                </span>
                <DiscoveryIndicator status={product.discovery_status} />
              </span>
            </div>
          </Link>

          <div className="flex shrink-0 items-center gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="hidden h-8 w-8 sm:inline-flex"
              disabled={isRefreshing}
              aria-label={isRefreshing ? 'Refreshing product' : 'Refresh product'}
              onClick={() => refresh.mutate()}
            >
              <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
            </Button>
            <ProductActionsMenu
              product={product}
              refreshing={isRefreshing}
              onRefresh={() => refresh.mutate()}
            />
          </div>
        </div>
      </div>
    </motion.div>
  )
}
