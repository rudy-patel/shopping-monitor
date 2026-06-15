import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { useMotionEnabled } from '@/lib/motion'
import { cn } from '@/lib/utils'

export type StickerVariant =
  | 'cream'
  | 'brick'
  | 'mustard'
  | 'navy'
  | 'sage'
  | 'pink'
  | 'cocoa'
  | 'slate'
  | 'lavender'

export type StickerShape = 'note' | 'pill' | 'tag' | 'ticket'

const variantClasses: Record<StickerVariant, string> = {
  cream: 'bg-amber-50 text-amber-900 border-amber-200/80',
  brick: 'bg-red-400 text-red-50 border-red-500/70',
  mustard: 'bg-yellow-200 text-amber-900 border-yellow-300/80',
  navy: 'bg-blue-700 text-blue-50 border-blue-800/70',
  sage: 'bg-emerald-100 text-emerald-900 border-emerald-200/80',
  pink: 'bg-pink-200 text-pink-900 border-pink-300/80',
  cocoa: 'bg-amber-700 text-amber-50 border-amber-800/70',
  slate: 'bg-slate-200 text-slate-800 border-slate-300/80',
  lavender: 'bg-violet-200 text-violet-900 border-violet-300/80',
}

const shapeClasses: Record<StickerShape, string> = {
  note: 'rounded-md',
  pill: 'rounded-full',
  tag: 'rounded-md rounded-l-2xl',
  ticket: 'rounded-lg',
}

export interface FloatingStickerProps {
  /** Tailwind utility classes for positioning the sticker (e.g. `top-[12%] left-[8%]`). */
  position: string
  /** Rotation in degrees applied via inline transform. Defaults to `0`. */
  rotate?: number
  variant?: StickerVariant
  shape?: StickerShape
  /** Stagger delay (seconds) for the entrance animation. */
  delay?: number
  className?: string
  children: ReactNode
}

/**
 * A decorative floating sticker used on the marketing splash. Always rendered
 * `aria-hidden` so that screen readers skip the visual flair and focus on the
 * sign-in CTA.
 */
export function FloatingSticker({
  position,
  rotate = 0,
  variant = 'cream',
  shape = 'note',
  delay = 0,
  className,
  children,
}: FloatingStickerProps) {
  const motionEnabled = useMotionEnabled()

  const baseClasses = cn(
    // Decorative only — hidden on small screens so mobile keeps the focus on
    // the sign-in CTA.
    'pointer-events-none absolute hidden md:inline-flex select-none items-center gap-1.5 border px-3 py-1.5 text-xs font-medium leading-tight shadow-sm',
    shapeClasses[shape],
    variantClasses[variant],
    position,
    className,
  )

  if (!motionEnabled) {
    return (
      <div
        aria-hidden
        data-testid="login-splash-sticker"
        className={baseClasses}
        style={{ transform: `rotate(${rotate}deg)` }}
      >
        {children}
      </div>
    )
  }

  return (
    <motion.div
      aria-hidden
      data-testid="login-splash-sticker"
      className={baseClasses}
      initial={{ opacity: 0, scale: 0.85, rotate }}
      animate={{ opacity: 1, scale: 1, rotate }}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  )
}
