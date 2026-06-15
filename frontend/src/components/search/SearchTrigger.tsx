import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SearchTriggerProps {
  onActivate: () => void
}

function isMac(): boolean {
  if (typeof navigator === 'undefined') return false
  return /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent || '')
}

/**
 * Header search affordance. Visually a search input — semantically a button that
 * opens the SearchCommandDialog. Keyboard shortcut (⌘K / Ctrl+K) is wired in
 * TopNav so it works site-wide.
 */
export function SearchTrigger({ onActivate }: SearchTriggerProps) {
  const [shortcutKey, setShortcutKey] = useState('⌘K')

  useEffect(() => {
    setShortcutKey(isMac() ? '⌘K' : 'Ctrl K')
  }, [])

  return (
    <button
      type="button"
      onClick={onActivate}
      aria-label="Open search"
      className={cn(
        // hidden on mobile, flex from md+ — keep display utilities together to avoid Tailwind sort ambiguity.
        'group hidden h-10 w-full max-w-md items-center gap-2 rounded-full md:flex',
        'border border-border/60 bg-muted/40 px-4 text-left text-sm text-muted-foreground',
        'transition-all duration-200',
        'hover:border-border hover:bg-muted/70 hover:text-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      )}
    >
      <Search
        className="h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground"
        aria-hidden
      />
      <span className="flex-1 truncate">Search products…</span>
      <kbd className="hidden items-center gap-1 rounded border border-border/60 bg-background/80 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground sm:inline-flex">
        {shortcutKey}
      </kbd>
    </button>
  )
}

/** Compact mobile version of the trigger — just the search icon. */
export function SearchTriggerMobile({ onActivate }: SearchTriggerProps) {
  return (
    <button
      type="button"
      onClick={onActivate}
      aria-label="Open search"
      className={cn(
        'inline-flex h-11 w-11 items-center justify-center rounded-full text-muted-foreground md:hidden',
        'transition-colors hover:bg-accent hover:text-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      )}
    >
      <Search className="h-5 w-5" aria-hidden />
    </button>
  )
}
