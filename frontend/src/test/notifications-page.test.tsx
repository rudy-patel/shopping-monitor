import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './test-utils'
import type { NotificationItem } from '@/lib/notifications'

const mockMarkReadMutate = vi.fn()
const mockMarkReadMutateAsync = vi.fn().mockResolvedValue({ updated_count: 1 })
const mockActionMutate = vi.fn()

const discoveryNotification: NotificationItem = {
  id: 'notif-discovery',
  user_id: '00000000-0000-0000-0000-000000000001',
  product_id: 'product-1',
  listing_id: null,
  type: 'discovery_complete',
  payload: { auto_added_count: 2, needs_review_count: 1 },
  is_read: false,
  email_sent_at: null,
  created_at: '2026-06-14T12:00:00.000Z',
  product_title: 'Test Laptop',
  product_status: 'active',
}

const revisitNotification: NotificationItem = {
  id: 'notif-revisit',
  user_id: '00000000-0000-0000-0000-000000000001',
  product_id: 'product-2',
  listing_id: null,
  type: 'revisit_stale',
  payload: {},
  is_read: false,
  email_sent_at: null,
  created_at: '2026-06-13T12:00:00.000Z',
  product_title: 'Old Wishlist Item',
  product_status: 'active',
}

vi.mock('@/hooks/useNotifications', () => ({
  useNotifications: vi.fn(),
  useUnreadNotificationCount: vi.fn(() => ({ data: 0 })),
  useMarkNotificationsRead: vi.fn(),
  useNotificationAction: vi.fn(),
}))

import {
  useMarkNotificationsRead,
  useNotificationAction,
  useNotifications,
} from '@/hooks/useNotifications'

function mockNotificationsHook(
  overrides: Partial<ReturnType<typeof useNotifications>> = {},
) {
  vi.mocked(useNotifications).mockReturnValue({
    items: [discoveryNotification, revisitNotification],
    total: 2,
    unreadCount: 2,
    hasMore: false,
    loadMore: vi.fn(),
    isLoading: false,
    isFetching: false,
    isError: false,
    refetch: vi.fn(),
    ...overrides,
  })
}

describe('NotificationsPage', () => {
  beforeEach(() => {
    mockMarkReadMutate.mockClear()
    mockMarkReadMutateAsync.mockClear()
    mockActionMutate.mockClear()

    vi.mocked(useMarkNotificationsRead).mockReturnValue({
      mutate: mockMarkReadMutate,
      mutateAsync: mockMarkReadMutateAsync,
      isPending: false,
    } as ReturnType<typeof useMarkNotificationsRead>)

    vi.mocked(useNotificationAction).mockReturnValue({
      mutate: mockActionMutate,
      isPending: false,
    } as ReturnType<typeof useNotificationAction>)

    mockNotificationsHook()
  })

  it('renders notification rows', async () => {
    renderApp('/notifications', { authenticated: true })

    expect(await screen.findByText(/found 3 matches for test laptop/i)).toBeInTheDocument()
    expect(screen.getByText(/ready to let it go/i)).toBeInTheDocument()
    expect(screen.getAllByText(/^unread$/i).length).toBeGreaterThan(0)
  })

  it('calls mark-all-read when header action is clicked', async () => {
    const user = userEvent.setup()
    renderApp('/notifications', { authenticated: true })

    await user.click(screen.getByRole('button', { name: /mark all as read/i }))
    expect(mockMarkReadMutate).toHaveBeenCalledWith({ all: true })
  })

  it('marks notification read before navigating on row click', async () => {
    const user = userEvent.setup()
    renderApp('/notifications', { authenticated: true })

    await user.click(screen.getByRole('button', { name: /found 3 matches for test laptop/i }))

    await waitFor(() => {
      expect(mockMarkReadMutateAsync).toHaveBeenCalledWith({ ids: ['notif-discovery'] })
    })
  })

  it('calls keep and archive actions for revisit rows', async () => {
    const user = userEvent.setup()
    renderApp('/notifications', { authenticated: true })

    await user.click(screen.getByRole('button', { name: /keep on list/i }))
    expect(mockActionMutate).toHaveBeenCalledWith({
      id: 'notif-revisit',
      action: 'keep',
    })

    await user.click(screen.getByRole('button', { name: /^archive$/i }))
    expect(mockActionMutate).toHaveBeenCalledWith({
      id: 'notif-revisit',
      action: 'archive',
    })
  })

  it('shows load more when additional pages exist', async () => {
    const loadMore = vi.fn()
    mockNotificationsHook({
      items: [discoveryNotification],
      total: 25,
      hasMore: true,
      loadMore,
    })

    const user = userEvent.setup()
    renderApp('/notifications', { authenticated: true })

    await user.click(screen.getByRole('button', { name: /load more/i }))
    expect(loadMore).toHaveBeenCalled()
  })

  it('disables mark-all-read when there are no unread notifications', async () => {
    mockNotificationsHook({ unreadCount: 0 })
    renderApp('/notifications', { authenticated: true })

    expect(screen.getByRole('button', { name: /mark all as read/i })).toBeDisabled()
  })
})
