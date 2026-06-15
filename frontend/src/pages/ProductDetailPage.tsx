import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { BackLink } from '@/components/layout/BackLink'
import { Archive, RotateCcw, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CategoryField } from '@/components/products/CategoryField'
import { DeleteProductDialog } from '@/components/products/DeleteProductDialog'
import { DiscoveryIndicator } from '@/components/products/DiscoveryIndicator'
import { ListingCard } from '@/components/products/ListingCard'
import { NeedsReviewQueue } from '@/components/products/NeedsReviewQueue'
import { Sparkline } from '@/components/products/Sparkline'
import { ThresholdField } from '@/components/products/ThresholdField'
import { TrendChip, trendPriceClass } from '@/components/products/TrendChip'
import { ProductListRowSkeleton } from '@/components/products/ProductListRowSkeleton'
import {
  useArchiveProduct,
  useDeleteListing,
  useProduct,
  useRefreshProduct,
  useRestoreProduct,
} from '@/hooks/useProducts'
import { useFormatPriceCents } from '@/hooks/useFormatPriceCents'
import { activeListings, listingComparisonHints } from '@/lib/products'
import { retailerLabel } from '@/lib/format'
import { cn } from '@/lib/utils'

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: product, isLoading, isError } = useProduct(id)
  const refresh = useRefreshProduct(id ?? '')
  const archive = useArchiveProduct(id ?? '')
  const restore = useRestoreProduct(id ?? '')
  const removeListing = useDeleteListing(id ?? '')
  const formatPriceCents = useFormatPriceCents()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const isArchived = product?.status === 'archived'
  const isRefreshing = refresh.isPending
  const listings = product ? activeListings(product.listings) : []

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-6 md:py-8">
        <BackLink to="/">Back to dashboard</BackLink>
        <div className="mt-6">
          <ProductListRowSkeleton />
        </div>
      </div>
    )
  }

  if (isError || !product) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-6 md:py-8">
        <BackLink to="/">Back to dashboard</BackLink>
        <p className="mt-4 text-muted-foreground">Product not found.</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6 pb-28 md:py-8 md:pb-8">
      <BackLink to={isArchived ? '/history' : '/'}>
        {isArchived ? 'Back to archived' : 'Back to dashboard'}
      </BackLink>

      <div className={cn('mt-6 space-y-8', isRefreshing && 'opacity-80')}>
        {isArchived ? (
          <div className="rounded-lg border border-border bg-muted px-4 py-3 text-sm">
            This product is archived. Restore it to resume price tracking on your dashboard.
          </div>
        ) : null}

        <section className="space-y-4">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
              {product.title}
            </h1>
            {product.brand ? (
              <p className="text-muted-foreground">{product.brand}</p>
            ) : null}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
            <div className="flex items-baseline gap-2">
              <span
                className={cn(
                  'text-3xl font-semibold tabular-nums tracking-tight md:text-4xl',
                  trendPriceClass(product.trend.direction),
                )}
              >
                {formatPriceCents(product.best_price_cents)}
              </span>
              {product.best_retailer_slug ? (
                <span className="text-sm text-muted-foreground">
                  at {retailerLabel(product.best_retailer_slug)}
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <TrendChip trend={product.trend} />
              <Sparkline
                history={product.price_history_30d}
                currentPriceCents={product.best_price_cents}
                direction={product.trend.direction}
                daysOfData={product.trend.days_of_data}
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <DiscoveryIndicator status={product.discovery_status} />
            {product.needs_review_count > 0 ? (
              <Badge variant="outline">
                {product.needs_review_count} listing
                {product.needs_review_count === 1 ? '' : 's'} to review
              </Badge>
            ) : null}
          </div>
        </section>

        <NeedsReviewQueue product={product} />

        <section className="space-y-4" aria-labelledby="listings-heading">
          <h2
            id="listings-heading"
            className="border-b border-border pb-2 text-lg font-semibold tracking-tight"
          >
            Listings
          </h2>
          <div className="space-y-3">
            {listings.map((listing) => {
              const comparison = listingComparisonHints(listing, listings)
              return (
                <ListingCard
                  key={listing.id}
                  listing={listing}
                  isBestPrice={comparison.isBestPrice}
                  priceDeltaVsBestCents={comparison.priceDeltaVsBestCents}
                  onRemove={(listingId) => removeListing.mutate(listingId)}
                  isRemoving={
                    removeListing.isPending && removeListing.variables === listing.id
                  }
                />
              )
            })}
          </div>
        </section>

        <section className="space-y-4" aria-labelledby="settings-heading">
          <h2
            id="settings-heading"
            className="border-b border-border pb-2 text-lg font-semibold tracking-tight"
          >
            Settings
          </h2>
          <div className="grid gap-6 sm:grid-cols-2">
            <CategoryField productId={product.id} value={product.category} />
            <ThresholdField
              productId={product.id}
              value={product.notification_threshold_pct}
              effectiveDefault={product.effective_threshold_pct}
            />
          </div>
        </section>

        <section className="fixed bottom-20 left-0 right-0 z-30 border-t border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:static md:border-0 md:bg-transparent md:p-0 md:backdrop-blur-none">
          <div className="mx-auto flex max-w-5xl flex-wrap gap-2">
            <Button
              variant="default"
              className="h-11 flex-1 sm:flex-none"
              disabled={isRefreshing}
              onClick={() => refresh.mutate()}
            >
              {isRefreshing ? 'Refreshing…' : 'Refresh'}
            </Button>
            {!isArchived ? (
              <Button
                variant="outline"
                className="h-11 flex-1 sm:flex-none"
                disabled={archive.isPending}
                onClick={() => archive.mutate()}
              >
                <Archive className="mr-2 h-4 w-4" />
                Archive
              </Button>
            ) : (
              <Button
                variant="default"
                className="h-11 flex-1 sm:flex-none"
                disabled={restore.isPending}
                onClick={() => restore.mutate()}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Restore
              </Button>
            )}
            <Button
              variant="outline"
              className="h-11 flex-1 sm:flex-none"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </section>
      </div>

      <DeleteProductDialog
        productId={product.id}
        productTitle={product.title}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        redirectTo={isArchived ? '/history' : '/'}
      />
    </div>
  )
}
