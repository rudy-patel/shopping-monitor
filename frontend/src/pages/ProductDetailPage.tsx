import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Archive, RefreshCw, RotateCcw, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CategoryField } from '@/components/products/CategoryField'
import { DeleteProductDialog } from '@/components/products/DeleteProductDialog'
import { DiscoveryIndicator } from '@/components/products/DiscoveryIndicator'
import { ListingRow } from '@/components/products/ListingRow'
import { NeedsReviewQueue } from '@/components/products/NeedsReviewQueue'
import { ThresholdField } from '@/components/products/ThresholdField'
import { TrendChip } from '@/components/products/TrendChip'
import { ProductCardSkeleton } from '@/components/products/ProductCardSkeleton'
import { useArchiveProduct, useDeleteListing, useProduct, useRefreshProduct, useRestoreProduct } from '@/hooks/useProducts'
import { activeListings } from '@/lib/products'
import { cn } from '@/lib/utils'

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: product, isLoading, isError } = useProduct(id)
  const refresh = useRefreshProduct(id ?? '')
  const archive = useArchiveProduct(id ?? '')
  const restore = useRestoreProduct(id ?? '')
  const removeListing = useDeleteListing(id ?? '')
  const [deleteOpen, setDeleteOpen] = useState(false)
  const isArchived = product?.status === 'archived'

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <ProductCardSkeleton />
      </div>
    )
  }

  if (isError || !product) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <p className="text-muted-foreground">Product not found.</p>
        <Link to="/" className="mt-4 inline-block text-sm underline-offset-4 hover:underline">
          Back to dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <Link
        to={isArchived ? '/history' : '/'}
        className="text-sm text-muted-foreground underline-offset-4 hover:underline"
      >
        {isArchived ? 'Back to archived products' : 'Back to dashboard'}
      </Link>

      <div className={cn('mt-6 space-y-8', refresh.isPending && 'opacity-70')}>
        {isArchived ? (
          <div className="rounded-lg border border-border bg-muted px-4 py-3 text-sm">
            This product is archived. Restore it to resume price tracking on your dashboard.
          </div>
        ) : null}

        <section className="flex flex-col gap-6 sm:flex-row">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt=""
              className="h-40 w-40 rounded-lg border border-border object-cover"
            />
          ) : (
            <div className="h-40 w-40 rounded-lg border border-border bg-muted" />
          )}
          <div className="space-y-3">
            <h1 className="text-2xl font-semibold tracking-tight">{product.title}</h1>
            {product.brand ? (
              <p className="text-muted-foreground">{product.brand}</p>
            ) : null}
            <div className="flex flex-wrap items-center gap-2">
              <TrendChip trend={product.trend} />
              <DiscoveryIndicator status={product.discovery_status} />
              {product.needs_review_count > 0 ? (
                <Badge variant="outline">
                  {product.needs_review_count} listing
                  {product.needs_review_count === 1 ? '' : 's'} to review
                </Badge>
              ) : null}
            </div>
          </div>
        </section>

        <NeedsReviewQueue product={product} />

        <section className="space-y-4">
          <h2 className="border-b border-border pb-2 text-lg font-semibold tracking-tight">
            Listings
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Retailer</th>
                  <th className="py-2 pr-4 font-medium">Price</th>
                  <th className="py-2 pr-4 font-medium">Stock</th>
                  <th className="py-2 pr-4 font-medium">Last scraped</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 font-medium">Link</th>
                </tr>
              </thead>
              <tbody>
                {activeListings(product.listings).map((listing) => (
                  <ListingRow
                    key={listing.id}
                    listing={listing}
                    onRemove={(listingId) => removeListing.mutate(listingId)}
                    isRemoving={
                      removeListing.isPending && removeListing.variables === listing.id
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="border-b border-border pb-2 text-lg font-semibold tracking-tight">
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

        <section className="flex flex-wrap gap-3 border-t border-border pt-6">
          <Button
            variant="default"
            disabled={refresh.isPending}
            onClick={() => refresh.mutate()}
          >
            <RefreshCw className={cn('mr-2 h-4 w-4', refresh.isPending && 'animate-spin')} />
            Refresh
          </Button>
          {!isArchived ? (
            <Button
              variant="outline"
              disabled={archive.isPending}
              onClick={() => archive.mutate()}
            >
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </Button>
          ) : (
            <Button
              variant="default"
              disabled={restore.isPending}
              onClick={() => restore.mutate()}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Restore
            </Button>
          )}
          <Button variant="outline" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
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
