import { useNavigate } from 'react-router-dom'
import { NotificationRow, notificationDestination } from '@/components/notifications/NotificationRow'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useMarkNotificationsRead,
  useNotificationAction,
  useNotifications,
} from '@/hooks/useNotifications'
import type { NotificationItem } from '@/lib/notifications'

export function NotificationsPage() {
  const navigate = useNavigate()
  const { items, unreadCount, hasMore, loadMore, isLoading, isFetching } = useNotifications()
  const markRead = useMarkNotificationsRead()
  const notificationAction = useNotificationAction()

  const handleNavigate = async (notification: NotificationItem) => {
    const destination = notificationDestination(notification)
    if (!destination) return

    try {
      if (!notification.is_read) {
        await markRead.mutateAsync({ ids: [notification.id] })
      }
    } catch {
      return
    }
    navigate(destination)
  }

  const handleMarkAllRead = () => {
    markRead.mutate({ all: true })
  }

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
        <Button
          variant="outline"
          size="sm"
          disabled={unreadCount === 0 || markRead.isPending}
          onClick={handleMarkAllRead}
        >
          Mark all as read
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground">
          No notifications in the last 90 days. Price drops, discovery updates, and revisit prompts
          will show up here.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((notification) => (
            <NotificationRow
              key={notification.id}
              notification={notification}
              onNavigate={handleNavigate}
              onKeep={(id) => notificationAction.mutate({ id, action: 'keep' })}
              onArchive={(id) => notificationAction.mutate({ id, action: 'archive' })}
              actionPending={notificationAction.isPending}
            />
          ))}
        </div>
      )}

      {hasMore ? (
        <div className="mt-6 flex justify-center">
          <Button variant="outline" onClick={loadMore} disabled={isFetching}>
            {isFetching ? 'Loading…' : 'Load more'}
          </Button>
        </div>
      ) : null}
    </div>
  )
}
