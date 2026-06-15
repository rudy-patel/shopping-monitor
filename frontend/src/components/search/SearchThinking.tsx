import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useMotionEnabled } from '@/lib/motion'
import { cn } from '@/lib/utils'

const SEARCH_STATUS_MESSAGES = [
  'Scouring Canadian retailers…',
  'Checking Best Buy, Apple, Indigo, and more…',
  'Asking the internet nicely…',
  'Hunting for the best match…',
  'Good finds take a moment — hang tight…',
] as const

const MESSAGE_INTERVAL_MS = 2200
const STAGGER_DELAY_MS = 45

interface SearchThinkingProps {
  query: string
}

export function SearchThinking({ query }: SearchThinkingProps) {
  const motionEnabled = useMotionEnabled()
  const [messageIndex, setMessageIndex] = useState(0)

  useEffect(() => {
    setMessageIndex(0)
    const id = window.setInterval(() => {
      setMessageIndex((current) => (current + 1) % SEARCH_STATUS_MESSAGES.length)
    }, MESSAGE_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [query])

  const statusMessage = SEARCH_STATUS_MESSAGES[messageIndex]

  return (
    <div className="space-y-4" data-testid="search-loading">
      <div className="flex items-start gap-3 rounded-xl border border-border/50 bg-muted/20 px-4 py-3">
        <Sparkles
          className={cn(
            'mt-0.5 h-4 w-4 shrink-0 text-foreground',
            motionEnabled && 'animate-pulse',
          )}
          aria-hidden
        />
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium text-foreground">
            Searching for <span className="font-semibold">{query}</span>
          </p>
          <motion.p
            key={statusMessage}
            className="text-xs text-muted-foreground"
            aria-live="polite"
            initial={motionEnabled ? { opacity: 0, y: 4 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
          >
            {statusMessage}
          </motion.p>
        </div>
      </div>

      <ul className="space-y-2" aria-hidden>
        {[0, 1, 2].map((i) => (
          <li
            key={i}
            className={cn(
              'h-[88px] rounded-xl border border-border/40 bg-muted/30',
              motionEnabled && 'animate-pulse',
            )}
            style={{ animationDelay: `${i * STAGGER_DELAY_MS}ms` }}
          />
        ))}
      </ul>
    </div>
  )
}
