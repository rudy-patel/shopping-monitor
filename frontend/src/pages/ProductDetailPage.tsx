import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { BackLink } from '@/components/layout/BackLink'
import { Archive, RotateCcw, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DeleteProductDialog } from '@/components/products/DeleteProductDialog'
import { DiscoveryIndicator } from '@/components/products/DiscoveryIndicator'
import { ListingCard } from '@/components/products/ListingCard'
import { NeedsReviewQueue } from '@/components/products/NeedsReviewQueue'
import { ProductSettingsSection } from '@/components/products/ProductSettingsSection'
import { Sparkline } from '@/components/products/Sparkline'
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
import { categoryLabel } from '@/lib/categories'
import { formatRelativeTime, formatTrackingSince } from '@/lib/format'
import { activeListings, listingComparisonHints } from '@/lib/products'
import { RetailerIdentity } from '@/components/retailers/RetailerLogo'
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

      <div className={cn('mt-6', isRefreshing && 'opacity-80')}>
        {isArchived ? (
          <div className="mb-6 rounded-lg border border-border bg-muted px-4 py-3 text-sm">
            This product is archived. Restore it to resume price tracking on your dashboard.
          </div>
        ) : null}

        <section
          className="rounded-lg border border-border bg-card px-4 py-5 md:px-6 md:py-6"
          aria-label="Product summary"
        >
          <div className="space-y-5">
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
                    isArchived
                      ? 'text-muted-foreground'
                      : trendPriceClass(product.trend.direction),
                  )}
                >
                  {formatPriceCents(product.best_price_cents)}
                </span>
                {product.best_retailer_slug ? (
                  <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
                    <span>at</span>
                    <RetailerIdentity slug={product.best_retailer_slug} size="xs" />
                  </span>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <TrendChip trend={product.trend} />
                <DiscoveryIndicator status={product.discovery_status} />
                <Sparkline
                  history={product.price_history_30d}
                  currentPriceCents={product.best_price_cents}
                  direction={product.trend.direction}
                  daysOfData={product.trend.days_of_data}
                  paused={isArchived}
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="font-normal">
                {categoryLabel(product.category)}
              </Badge>
              <span>Tracking since {formatTrackingSince(product.created_at)}</span>
              <span aria-hidden="true">·</span>
              <span>
                Last refreshed{' '}
                {formatRelativeTime(product.last_refresh_at ?? product.last_scraped_at)}
              </span>
              {isArchived ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="text-muted-foreground">Tracking paused</span>
                </>
              ) : null}
            </div>

            {product.needs_review_count > 0 ? (
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">
                  {product.needs_review_count} listing
                  {product.needs_review_count === 1 ? '' : 's'} to review
                </Badge>
              </div>
            ) : null}
          </div>
        </section>

        <div className="mt-5 space-y-6">
          <NeedsReviewQueue product={product} />

          <section className="space-y-3" role="region" aria-labelledby="listings-heading">
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

          <ProductSettingsSection product={product} />
        </div>

        <section className="fixed bottom-20 left-0 right-0 z-30 border-t border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:static md:mt-8 md:border-0 md:bg-transparent md:p-0 md:backdrop-blur-none">
          <div className="mx-auto flex max-w-5xl items-center gap-3">
            <div className="flex min-w-0 items-baseline gap-2 md:hidden">
              <span
                className={cn(
                  'truncate text-lg font-semibold tabular-nums tracking-tight',
                  isArchived
                    ? 'text-muted-foreground'
                    : trendPriceClass(product.trend.direction),
                )}
              >
                {formatPriceCents(product.best_price_cents)}
              </span>
              <TrendChip trend={product.trend} className="shrink-0" />
            </div>
            <div className="ml-auto flex flex-wrap justify-end gap-2">
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
