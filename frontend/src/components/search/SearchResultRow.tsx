import { useState } from 'react'
import { ArrowUpRight, Check, Loader2, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useMotionEnabled } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { RetailerLogo } from '@/components/retailers/RetailerLogo'
import { retailerLabelFromUrl } from '@/lib/format'
import type { SearchResultItem } from '@/lib/search'

export interface SearchResultRowProps {
  item: SearchResultItem
  isPending: boolean
  isSucceeded: boolean
  onTrack: (item: SearchResultItem) => void
}

export function SearchResultRow({
  item,
  isPending,
  isSucceeded,
  onTrack,
}: SearchResultRowProps) {
  const motionEnabled = useMotionEnabled()
  const [isHovering, setIsHovering] = useState(false)

  const retailerDisplay = item.supported
    ? item.retailer_label
    : retailerLabelFromUrl(item.url, item.retailer_label)

  return (
    <motion.li
      layout
      initial={motionEnabled ? { opacity: 0, y: 8 } : false}
      animate={{ opacity: 1, y: 0 }}
      exit={motionEnabled ? { opacity: 0, y: -8 } : undefined}
      transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
      onHoverStart={() => setIsHovering(true)}
      onHoverEnd={() => setIsHovering(false)}
      className={cn(
        'group relative grid grid-cols-[1fr_auto] gap-3 rounded-xl border border-border/50 bg-background/40 p-4',
        'transition-all duration-200 hover:border-border hover:bg-background/80',
        isHovering && motionEnabled && 'shadow-sm',
      )}
      data-testid="search-result-row"
    >
      <div className="min-w-0 space-y-1.5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Badge
            variant={item.supported ? 'default' : 'outline'}
            className={cn(
              'h-5 gap-1 px-2 text-[10px] font-medium uppercase tracking-wide',
              !item.supported && 'border-dashed text-muted-foreground',
            )}
            data-testid="retailer-badge"
          >
            {item.supported ? <RetailerLogo slug={item.retailer_slug} size="xs" /> : null}
            {retailerDisplay}
          </Badge>
          {item.brand_hint ? (
            <span className="text-muted-foreground">· {item.brand_hint}</span>
          ) : null}
          {!item.supported ? (
            <span className="text-[10px] text-muted-foreground/80">
              Best-effort tracking
            </span>
          ) : null}
        </div>
        <p
          className="line-clamp-2 text-sm font-medium leading-snug text-foreground"
          data-testid="result-title"
        >
          {item.title}
        </p>
        {item.justification ? (
          <p className="line-clamp-1 text-xs text-muted-foreground">
            <Sparkles className="mr-1 inline h-3 w-3 align-[-2px]" aria-hidden />
            {item.justification}
          </p>
        ) : null}
      </div>

      <div className="flex items-end gap-1.5">
        <Button
          variant="outline"
          size="sm"
          className="h-8 rounded-full px-3 text-xs"
          asChild
        >
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open ${item.title} on ${retailerDisplay}`}
            onClick={(event) => event.stopPropagation()}
          >
            Open
            <ArrowUpRight className="ml-1 h-3 w-3" aria-hidden />
          </a>
        </Button>
        <Button
          type="button"
          size="sm"
          className="h-8 rounded-full px-3 text-xs"
          onClick={() => onTrack(item)}
          disabled={isPending || isSucceeded}
          aria-label={`Track ${item.title}`}
          data-testid="track-button"
        >
          {isSucceeded ? (
            <>
              <Check className="mr-1 h-3.5 w-3.5" aria-hidden />
              Tracking
            </>
          ) : isPending ? (
            <>
              <Loader2
                className={cn('mr-1 h-3.5 w-3.5', motionEnabled && 'animate-spin')}
                aria-hidden
              />
              Adding…
            </>
          ) : (
            'Track'
          )}
        </Button>
      </div>
    </motion.li>
  )
}
