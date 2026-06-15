import {
  Bell,
  CalendarHeart,
  Eye,
  Heart,
  Hourglass,
  ShoppingBag,
  Sparkles,
  Star,
  Tag,
  TrendingDown,
  type LucideIcon,
} from 'lucide-react'
import { FloatingSticker } from '@/components/login/FloatingSticker'
import { loginSplashStickers, type LoginStickerIcon } from '@/lib/login-stickers'
import { cn } from '@/lib/utils'

const stickerIcons: Record<LoginStickerIcon, LucideIcon> = {
  bell: Bell,
  'calendar-heart': CalendarHeart,
  eye: Eye,
  heart: Heart,
  hourglass: Hourglass,
  'shopping-bag': ShoppingBag,
  sparkles: Sparkles,
  star: Star,
  tag: Tag,
  'trending-down': TrendingDown,
}

function StickerTicket({
  kicker,
  title,
  kickerClassName,
}: {
  kicker: string
  title: string
  kickerClassName?: string
}) {
  return (
    <span className="flex flex-col leading-tight">
      <span
        className={cn(
          'text-[10px] uppercase tracking-widest opacity-70',
          kickerClassName,
        )}
      >
        {kicker}
      </span>
      <span className="text-sm font-semibold">{title}</span>
    </span>
  )
}

export function LoginSplashStickers() {
  return (
    <>
      {loginSplashStickers.map((sticker) => {
        const Icon = sticker.icon ? stickerIcons[sticker.icon] : null

        return (
          <FloatingSticker
            key={`${sticker.position}-${sticker.label ?? sticker.ticket?.title}`}
            position={sticker.position}
            rotate={sticker.rotate}
            variant={sticker.variant}
            shape={sticker.shape}
            delay={sticker.delay}
          >
            {Icon ? (
              <Icon className={cn('h-3.5 w-3.5', sticker.iconClassName)} />
            ) : null}
            {sticker.ticket ? (
              <StickerTicket
                kicker={sticker.ticket.kicker}
                title={sticker.ticket.title}
                kickerClassName={
                  sticker.variant === 'navy' ? 'opacity-80' : undefined
                }
              />
            ) : sticker.label ? (
              <span className={sticker.labelClassName}>{sticker.label}</span>
            ) : null}
          </FloatingSticker>
        )
      })}
    </>
  )
}
