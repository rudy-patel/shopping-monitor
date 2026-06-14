import { notificationDestination } from '@/components/notifications/NotificationRow'
import type { NotificationItem } from '@/lib/notifications'

function makeNotification(
  overrides: Partial<NotificationItem> = {},
): NotificationItem {
  return {
    id: 'notif-1',
    user_id: '00000000-0000-0000-0000-000000000001',
    product_id: 'product-1',
    listing_id: null,
    type: 'discovery_complete',
    payload: {},
    is_read: false,
    email_sent_at: null,
    created_at: '2026-06-14T12:00:00.000Z',
    product_title: 'Test Product',
    product_status: 'active',
    ...overrides,
  }
}

describe('notificationDestination', () => {
  it('routes needs_input to the variant picker', () => {
    expect(
      notificationDestination(makeNotification({ type: 'needs_input' })),
    ).toBe('/products/product-1/variants')
  })

  it('routes discovery_complete to product detail', () => {
    expect(
      notificationDestination(makeNotification({ type: 'discovery_complete' })),
    ).toBe('/products/product-1')
  })

  it('returns null for revisit prompts', () => {
    expect(
      notificationDestination(makeNotification({ type: 'revisit_stale' })),
    ).toBeNull()
    expect(
      notificationDestination(makeNotification({ type: 'revisit_on_sale' })),
    ).toBeNull()
  })

  it('returns null when product_id is missing', () => {
    expect(
      notificationDestination(makeNotification({ product_id: null })),
    ).toBeNull()
  })
})
