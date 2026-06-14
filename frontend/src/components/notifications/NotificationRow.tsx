import { Button } from '@/components/ui/button'
import { formatPriceCents, formatRelativeTime, retailerLabel } from '@/lib/format'
import type { NotificationItem } from '@/lib/notifications'

interface NotificationRowProps {
  notification: NotificationItem
  onNavigate?: (notification: NotificationItem) => void
  onKeep?: (id: string) => void
  onArchive?: (id: string) => void
  actionPending?: boolean
}

function discoveryCopy(notification: NotificationItem): string {
  const autoAdded = Number(notification.payload.auto_added_count ?? 0)
  const needsReview = Number(notification.payload.needs_review_count ?? 0)
  const title = notification.product_title ?? 'this product'
  if (needsReview > 0) {
    return `Found ${autoAdded + needsReview} matches for ${title}. ${needsReview} need your review.`
  }
  return `Found ${autoAdded} new retailer match${autoAdded === 1 ? '' : 'es'} for ${title}.`
}

function priceDropCopy(notification: NotificationItem): string {
  const oldPrice = Number(notification.payload.old_price_cents ?? 0)
  const newPrice = Number(notification.payload.new_price_cents ?? 0)
  const title = notification.product_title ?? 'A product'
  return `${title} dropped from ${formatPriceCents(oldPrice)} to ${formatPriceCents(newPrice)}.`
}

function backInStockCopy(notification: NotificationItem): string {
  const retailer = retailerLabel(String(notification.payload.retailer_slug ?? ''))
  const title = notification.product_title ?? 'A product'
  return `${title} is back in stock at ${retailer}.`
}

function scrapeFailingCopy(notification: NotificationItem): string {
  const title = notification.product_title ?? 'A product'
  return `We could not refresh prices for ${title}. We will keep trying on the daily check.`
}

function revisitOnSaleCopy(notification: NotificationItem): string {
  const title = notification.product_title ?? 'this item'
  return `${title} has been on your list a while and is on sale now. Still want it?`
}

function revisitStaleCopy(notification: NotificationItem): string {
  const title = notification.product_title ?? 'this item'
  return `${title} has been sitting on your list without much attention. Ready to let it go?`
}

function notificationCopy(notification: NotificationItem): string {
  switch (notification.type) {
    case 'discovery_complete':
      return discoveryCopy(notification)
    case 'needs_input':
      return `Choose a variant for ${notification.product_title ?? 'this product'}.`
    case 'price_drop':
      return priceDropCopy(notification)
    case 'back_in_stock':
      return backInStockCopy(notification)
    case 'scrape_failing':
      return scrapeFailingCopy(notification)
    case 'revisit_on_sale':
      return revisitOnSaleCopy(notification)
    case 'revisit_stale':
      return revisitStaleCopy(notification)
    default:
      return 'Update available.'
  }
}

export function notificationDestination(notification: NotificationItem): string | null {
  if (!notification.product_id) return null
  switch (notification.type) {
    case 'needs_input':
      return `/products/${notification.product_id}/variants`
    case 'discovery_complete':
    case 'price_drop':
    case 'back_in_stock':
    case 'scrape_failing':
      return `/products/${notification.product_id}`
    default:
      return null
  }
}

function isRevisitType(type: NotificationItem['type']) {
  return type === 'revisit_on_sale' || type === 'revisit_stale'
}

export function NotificationRow({
  notification,
  onNavigate,
  onKeep,
  onArchive,
  actionPending = false,
}: NotificationRowProps) {
  const destination = notificationDestination(notification)
  const revisit = isRevisitType(notification.type)
  const copy = notificationCopy(notification)

  const content = (
    <>
      <p className={notification.is_read ? 'text-muted-foreground' : 'font-medium'}>{copy}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {formatRelativeTime(notification.created_at)}
      </p>
    </>
  )

  if (revisit) {
    return (
      <article
        className={`rounded-lg border border-border p-4 ${
          notification.is_read ? 'opacity-80' : 'border-l-4 border-l-foreground'
        }`}
      >
        {content}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={actionPending}
            onClick={() => onKeep?.(notification.id)}
          >
            Keep on list
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={actionPending}
            onClick={() => onArchive?.(notification.id)}
          >
            Archive
          </Button>
        </div>
      </article>
    )
  }

  if (destination && onNavigate) {
    return (
      <button
        type="button"
        onClick={() => onNavigate(notification)}
        className={`block w-full rounded-lg border border-border p-4 text-left transition-colors hover:bg-muted/50 ${
          notification.is_read ? 'opacity-80' : 'border-l-4 border-l-foreground'
        }`}
      >
        {content}
      </button>
    )
  }

  return (
    <article
      className={`rounded-lg border border-border p-4 ${
        notification.is_read ? 'opacity-80' : 'border-l-4 border-l-foreground'
      }`}
    >
      {content}
    </article>
  )
}
