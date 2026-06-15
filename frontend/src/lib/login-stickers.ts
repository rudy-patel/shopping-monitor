import type { StickerShape, StickerVariant } from '@/components/login/FloatingSticker'

export type LoginStickerIcon =
  | 'bell'
  | 'calendar-heart'
  | 'eye'
  | 'heart'
  | 'hourglass'
  | 'shopping-bag'
  | 'sparkles'
  | 'star'
  | 'tag'
  | 'trending-down'

export interface LoginStickerDef {
  position: string
  rotate: number
  variant: StickerVariant
  shape: StickerShape
  delay: number
  icon?: LoginStickerIcon
  iconClassName?: string
  label?: string
  labelClassName?: string
  ticket?: { kicker: string; title: string }
}

/** Decorative sticker layout for the sign-in splash (desktop only). */
export const loginSplashStickers: LoginStickerDef[] = [
  {
    position: 'top-[7%] left-[6%]',
    rotate: -12,
    variant: 'brick',
    shape: 'pill',
    delay: 0.05,
    icon: 'tag',
    label: '−20% OFF',
    labelClassName: 'text-sm font-semibold tracking-wide',
  },
  {
    position: 'top-[19%] left-[18%]',
    rotate: 6,
    variant: 'pink',
    shape: 'note',
    delay: 0.1,
    icon: 'heart',
    iconClassName: 'fill-current',
    label: 'Wishlist',
  },
  {
    position: 'top-[6%] left-[42%]',
    rotate: -3,
    variant: 'mustard',
    shape: 'ticket',
    delay: 0.15,
    ticket: { kicker: 'Sale ends', title: '48 hours' },
  },
  {
    position: 'top-[10%] right-[8%]',
    rotate: -8,
    variant: 'cream',
    shape: 'note',
    delay: 0.2,
    icon: 'bell',
    label: 'Alert set',
  },
  {
    position: 'top-[20%] right-[24%]',
    rotate: 7,
    variant: 'navy',
    shape: 'ticket',
    delay: 0.25,
    icon: 'calendar-heart',
    ticket: { kicker: 'Nov 28', title: 'Black Friday' },
  },
  {
    position: 'top-[38%] left-[4%]',
    rotate: -5,
    variant: 'slate',
    shape: 'note',
    delay: 0.3,
    icon: 'eye',
    label: 'Watching…',
  },
  {
    position: 'top-[40%] right-[5%]',
    rotate: 7,
    variant: 'sage',
    shape: 'note',
    delay: 0.35,
    icon: 'hourglass',
    label: 'Worth the wait',
  },
  {
    position: 'top-[58%] left-[14%]',
    rotate: 8,
    variant: 'sage',
    shape: 'tag',
    delay: 0.4,
    icon: 'trending-down',
    label: '−$45',
    labelClassName: 'font-mono text-sm font-semibold',
  },
  {
    position: 'top-[56%] right-[18%]',
    rotate: -6,
    variant: 'mustard',
    shape: 'pill',
    delay: 0.45,
    icon: 'star',
    iconClassName: 'fill-current',
    label: 'Favourite',
  },
  {
    position: 'top-[74%] left-[8%]',
    rotate: -9,
    variant: 'cocoa',
    shape: 'ticket',
    delay: 0.5,
    label: 'Patience pays',
    labelClassName: 'text-[11px] font-semibold uppercase tracking-[0.18em]',
  },
  {
    position: 'top-[72%] right-[8%]',
    rotate: 6,
    variant: 'lavender',
    shape: 'note',
    delay: 0.55,
    icon: 'shopping-bag',
    label: 'Someday',
  },
  {
    position: 'bottom-[7%] left-[28%]',
    rotate: 4,
    variant: 'cream',
    shape: 'note',
    delay: 0.6,
    icon: 'sparkles',
    label: 'Maybe tomorrow',
  },
  {
    position: 'bottom-[10%] right-[28%]',
    rotate: -4,
    variant: 'pink',
    shape: 'ticket',
    delay: 0.65,
    ticket: { kicker: 'Order #007', title: 'Tracking…' },
  },
]
