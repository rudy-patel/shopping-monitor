import { ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  useAcceptListing,
  useRejectListing,
} from '@/hooks/useProducts'
import { formatPriceCents, retailerLabel } from '@/lib/format'
import type { Listing, ProductDetail } from '@/lib/products'
import { needsReviewListings } from '@/lib/products'

interface NeedsReviewQueueProps {
  product: ProductDetail
}

function stockLabel(inStock: boolean | null): string {
  if (inStock === true) return 'In stock'
  if (inStock === false) return 'Out of stock'
  return 'Unknown'
}

function candidateImage(listing: Listing, product: ProductDetail): string | null {
  return listing.review_image_url ?? product.image_url ?? null
}

function candidateTitle(listing: Listing): string {
  return listing.review_title ?? retailerLabel(listing.retailer_slug)
}

export function NeedsReviewQueue({ product }: NeedsReviewQueueProps) {
  const queue = needsReviewListings(product.listings)
  const accept = useAcceptListing(product.id)
  const reject = useRejectListing(product.id)

  if (queue.length === 0) {
    return null
  }

  const acceptingId = accept.isPending ? accept.variables : undefined
  const rejectingId = reject.isPending ? reject.variables : undefined

  return (
    <section className="space-y-4">
      <h2 className="border-b border-border pb-2 text-lg font-semibold tracking-tight">
        Needs review ({queue.length})
      </h2>
      <ul className="space-y-4">
        {queue.map((listing) => {
          const imageUrl = candidateImage(listing, product)
          const reason = listing.review_reason ?? 'Possible match'
          const confidencePct =
            listing.match_confidence != null
              ? `${Math.round(listing.match_confidence * 100)}% match`
              : null
          const cardPending =
            acceptingId === listing.id || rejectingId === listing.id

          return (
            <li
              key={listing.id}
              className="rounded-lg border border-border p-4"
            >
              <div className="flex flex-col gap-4 sm:flex-row">
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt=""
                    className="h-20 w-20 shrink-0 rounded-md border border-border object-cover"
                  />
                ) : (
                  <div className="h-20 w-20 shrink-0 rounded-md border border-border bg-muted" />
                )}
                <div className="min-w-0 flex-1 space-y-2">
                  <p className="font-medium">{candidateTitle(listing)}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatPriceCents(listing.last_known_price_cents)} ·{' '}
                    {stockLabel(listing.is_in_stock)}
                  </p>
                  <p className="text-sm italic text-muted-foreground">&ldquo;{reason}&rdquo;</p>
                  {confidencePct ? (
                    <p className="text-xs text-muted-foreground">{confidencePct}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button
                      size="sm"
                      disabled={cardPending}
                      onClick={() => accept.mutate(listing.id)}
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={cardPending}
                      onClick={() => reject.mutate(listing.id)}
                    >
                      Reject
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                      <a
                        href={listing.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open source
                        <ExternalLink className="ml-1 h-3 w-3" />
                      </a>
                    </Button>
                  </div>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
