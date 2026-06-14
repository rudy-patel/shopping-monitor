import { useCallback, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  applyNotificationAction,
  listNotifications,
  markNotificationsRead,
  notificationsQueryKey,
  notificationsUnreadQueryKey,
  type NotificationItem,
  type NotificationsListResponse,
} from '@/lib/notifications'
import { productQueryKey } from '@/lib/products'

const DEFAULT_PAGE_SIZE = 20

function patchNotificationCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  updater: (items: NotificationItem[]) => {
    items: NotificationItem[]
    unreadDelta: number
  },
): number {
  let totalUnreadDelta = 0
  queryClient.setQueriesData<NotificationsListResponse>(
    { queryKey: ['notifications'] },
    (current: NotificationsListResponse | undefined) => {
      if (!current) return current
      const { items, unreadDelta } = updater(current.items)
      totalUnreadDelta = unreadDelta
      return {
        ...current,
        items,
        unread_count: Math.max(0, current.unread_count + unreadDelta),
      }
    },
  )
  return totalUnreadDelta
}

export function useNotifications({ limit = DEFAULT_PAGE_SIZE } = {}) {
  const [offset, setOffset] = useState(0)
  const [mergedItems, setMergedItems] = useState<NotificationItem[]>([])

  const query = useQuery({
    queryKey: notificationsQueryKey({ limit, offset }),
    queryFn: () => listNotifications({ limit, offset }),
  })

  useEffect(() => {
    const data = query.data
    if (!data) return
    setMergedItems((previous) => {
      if (offset === 0) return data.items
      const existingIds = new Set(previous.map((item: NotificationItem) => item.id))
      const appended = data.items.filter((item: NotificationItem) => !existingIds.has(item.id))
      return [...previous, ...appended]
    })
  }, [query.data, offset])

  const total = query.data?.total ?? 0
  const unreadCount = query.data?.unread_count ?? 0
  const hasMore = mergedItems.length < total

  const loadMore = useCallback(() => {
    if (!hasMore || query.isFetching) return
    setOffset((current) => current + limit)
  }, [hasMore, limit, query.isFetching])

  return {
    items: mergedItems,
    total,
    unreadCount,
    hasMore,
    loadMore,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
  }
}

export function useUnreadNotificationCount() {
  return useQuery({
    queryKey: notificationsUnreadQueryKey,
    queryFn: async () => {
      const data = await listNotifications({ limit: 1, offset: 0 })
      return data.unread_count
    },
    staleTime: 60_000,
    refetchOnWindowFocus: true,
    refetchInterval: false,
  })
}

export function useMarkNotificationsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: markNotificationsRead,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ['notifications'] })

      const markIds = variables.all
        ? null
        : new Set(variables.ids ?? [])

      const unreadDelta = patchNotificationCaches(queryClient, (items) => {
        let delta = 0
        const nextItems = items.map((item) => {
          const shouldMark = variables.all || (markIds?.has(item.id) ?? false)
          if (shouldMark && !item.is_read) {
            delta -= 1
            return { ...item, is_read: true }
          }
          return item
        })
        return { items: nextItems, unreadDelta: delta }
      })

      const previousUnread = queryClient.getQueryData<number>(notificationsUnreadQueryKey)
      if (variables.all) {
        queryClient.setQueryData(notificationsUnreadQueryKey, 0)
      } else if (previousUnread != null && unreadDelta !== 0) {
        queryClient.setQueryData(
          notificationsUnreadQueryKey,
          Math.max(0, previousUnread + unreadDelta),
        )
      }

      return { previousUnread }
    },
    onError: (_error, _vars, context) => {
      if (context?.previousUnread != null) {
        queryClient.setQueryData(notificationsUnreadQueryKey, context.previousUnread)
      }
      toast.error('Could not update notifications')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useNotificationAction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'keep' | 'archive' }) =>
      applyNotificationAction(id, action),
    onMutate: async ({ id, action }) => {
      await queryClient.cancelQueries({ queryKey: ['notifications'] })

      let productId: string | null = null

      const unreadDelta = patchNotificationCaches(queryClient, (items) => {
        let delta = 0
        const nextItems = items.map((item) => {
          if (item.id !== id) return item
          productId = item.product_id
          if (!item.is_read) delta -= 1
          return { ...item, is_read: true }
        })
        return { items: nextItems, unreadDelta: delta }
      })

      const previousUnread = queryClient.getQueryData<number>(notificationsUnreadQueryKey)
      if (previousUnread != null && unreadDelta !== 0) {
        queryClient.setQueryData(
          notificationsUnreadQueryKey,
          Math.max(0, previousUnread + unreadDelta),
        )
      }

      return { previousUnread, productId, action }
    },
    onSuccess: (_data, variables, context) => {
      if (variables.action === 'archive' && context?.productId) {
        queryClient.invalidateQueries({ queryKey: productQueryKey(context.productId) })
        queryClient.invalidateQueries({ queryKey: ['products'] })
      }
    },
    onError: (_error, _vars, context) => {
      if (context?.previousUnread != null) {
        queryClient.setQueryData(notificationsUnreadQueryKey, context.previousUnread)
      }
      toast.error('Could not complete action')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}
