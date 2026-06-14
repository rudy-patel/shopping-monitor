import { apiFetch } from '@/lib/api'

export type NotificationType =
  | 'price_drop'
  | 'back_in_stock'
  | 'discovery_complete'
  | 'needs_input'
  | 'scrape_failing'
  | 'revisit_on_sale'
  | 'revisit_stale'

export interface NotificationItem {
  id: string
  user_id: string
  product_id: string | null
  listing_id: string | null
  type: NotificationType
  payload: Record<string, unknown>
  is_read: boolean
  email_sent_at: string | null
  created_at: string
  product_title: string | null
  product_status: string | null
}

export interface NotificationsListResponse {
  items: NotificationItem[]
  unread_count: number
  total: number
  limit: number
  offset: number
}

export interface ListNotificationsParams {
  limit?: number
  offset?: number
  unreadOnly?: boolean
}

export interface MarkReadResponse {
  updated_count: number
}

export interface NotificationActionResponse {
  notification_id: string
  action: 'keep' | 'archive'
}

export function notificationsQueryKey(params?: ListNotificationsParams) {
  return ['notifications', params ?? {}] as const
}

export const notificationsUnreadQueryKey = ['notifications', 'unread-count'] as const

export function listNotifications(
  params: ListNotificationsParams = {},
): Promise<NotificationsListResponse> {
  const search = new URLSearchParams()
  if (params.limit != null) search.set('limit', String(params.limit))
  if (params.offset != null) search.set('offset', String(params.offset))
  if (params.unreadOnly) search.set('unread_only', 'true')
  const query = search.toString()
  return apiFetch<NotificationsListResponse>(
    `/api/notifications${query ? `?${query}` : ''}`,
  )
}

export function markNotificationsRead(input: {
  ids?: string[]
  all?: boolean
}): Promise<MarkReadResponse> {
  return apiFetch<MarkReadResponse>('/api/notifications/mark-read', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function applyNotificationAction(
  id: string,
  action: 'keep' | 'archive',
): Promise<NotificationActionResponse> {
  return apiFetch<NotificationActionResponse>(`/api/notifications/${id}/action`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
}
