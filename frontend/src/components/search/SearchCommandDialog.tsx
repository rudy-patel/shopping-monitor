import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Link2, Search, Sparkles, X } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { useCreateProduct } from '@/hooks/useProducts'
import { useSearch } from '@/hooks/useSearch'
import { useMotionEnabled } from '@/lib/motion'
import { isSearchableQuery, type SearchResultItem } from '@/lib/search'
import { cn } from '@/lib/utils'
import { SearchResultRow } from './SearchResultRow'
import { SearchThinking } from './SearchThinking'

const EXAMPLE_QUERIES = [
  'AirPods Pro',
  'Nintendo Switch 2',
  'Lenovo Yoga laptop',
  'Patagonia jacket',
] as const

const STAGGER_DELAY_MS = 45
const EMPTY_FOOTNOTE = 'ESC to close · Powered by AI'

interface SearchCommandDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onRequestUrlAdd: () => void
}

export function SearchCommandDialog({
  open,
  onOpenChange,
  onRequestUrlAdd,
}: SearchCommandDialogProps) {
  const motionEnabled = useMotionEnabled()
  const inputRef = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [pendingItem, setPendingItem] = useState<string | null>(null)
  const [trackedItem, setTrackedItem] = useState<string | null>(null)

  const createProduct = useCreateProduct()

  const { data, isFetching, isError, error } = useSearch(submittedQuery)

  useEffect(() => {
    if (!open) {
      setDraft('')
      setSubmittedQuery('')
      setPendingItem(null)
      setTrackedItem(null)
    }
  }, [open])

  // Focus the input the first frame the dialog opens (Radix manages most focus,
  // but we still want it to be in the input, not the close button).
  useEffect(() => {
    if (!open) return
    const id = window.setTimeout(() => inputRef.current?.focus(), 50)
    return () => window.clearTimeout(id)
  }, [open])

  const canSubmit = isSearchableQuery(draft) && draft.trim() !== submittedQuery
  const results: SearchResultItem[] = data?.results ?? []

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!isSearchableQuery(trimmed)) return
    setSubmittedQuery(trimmed)
    setTrackedItem(null)
  }

  const handleExampleClick = (example: string) => {
    setDraft(example)
    setSubmittedQuery(example)
    setTrackedItem(null)
    inputRef.current?.focus()
  }

  const handleTrack = (item: SearchResultItem) => {
    if (createProduct.isPending) return
    setPendingItem(item.url)
    const seed = results
      .filter((other) => other.supported && other.url !== item.url)
      .slice(0, 4)
      .map(({ retailer_slug, url }) => ({ retailer_slug, url }))
    createProduct.mutate(
      {
        url: item.url,
        category: 'auto',
        ...(seed.length > 0 ? { discovery_seed: seed } : {}),
      },
      {
        onSuccess: () => {
          setTrackedItem(item.url)
          // Brief delay so the user sees the success state, then the dialog closes
          // and navigation (handled in useCreateProduct) takes over.
          window.setTimeout(() => onOpenChange(false), 250)
        },
        onSettled: () => setPendingItem(null),
      },
    )
  }

  const handleAddByUrl = () => {
    onOpenChange(false)
    // Wait for the dialog close animation so focus transfers cleanly.
    window.setTimeout(onRequestUrlAdd, 180)
  }

  const isSearching = isSearchableQuery(submittedQuery) && isFetching

  const renderStateView = () => {
    if (!isSearchableQuery(submittedQuery) && !isSearching) {
      return (
        <IdleState
          onExampleClick={handleExampleClick}
          onAddByUrl={handleAddByUrl}
        />
      )
    }
    if (isSearching) {
      return <SearchThinking query={submittedQuery} />
    }
    if (isError) {
      return <ErrorState error={error} motionEnabled={motionEnabled} />
    }
    if (results.length === 0) {
      return <EmptyState query={submittedQuery} onAddByUrl={handleAddByUrl} />
    }
    return (
      <ResultsList
        items={results}
        pendingUrl={pendingItem}
        trackedUrl={trackedItem}
        onTrack={handleTrack}
        motionEnabled={motionEnabled}
      />
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (createProduct.isPending) return
        onOpenChange(next)
      }}
    >
      <DialogContent
        className={cn(
          'top-[12%] translate-y-0 sm:top-[18%]',
          'max-w-2xl gap-0 overflow-hidden border-border/60 bg-background/95 p-0',
          'shadow-2xl backdrop-blur',
          // Hide the default Radix close X — search has its own clear/submit affordances.
          '[&>button]:hidden',
        )}
        onInteractOutside={(e) => {
          if (createProduct.isPending) e.preventDefault()
        }}
        onEscapeKeyDown={(e) => {
          if (createProduct.isPending) e.preventDefault()
        }}
      >
        <DialogTitle className="sr-only">Search products</DialogTitle>
        <DialogDescription className="sr-only">
          Search Canadian retailers for any product. Track to start monitoring price
          and availability.
        </DialogDescription>

        <form
          onSubmit={handleSubmit}
          className="border-b border-border/60 px-4 py-3"
        >
          <div className="flex items-center gap-3">
            <Sparkles
              className={cn(
                'h-4 w-4 shrink-0 text-muted-foreground',
                motionEnabled && isSearching && 'animate-pulse text-foreground',
              )}
              aria-hidden
            />
            <input
              ref={inputRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              type="text"
              placeholder="Search any product across Canadian retailers…"
              className={cn(
                'flex-1 bg-transparent text-base outline-none',
                'placeholder:text-muted-foreground/70',
              )}
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              aria-label="Search products"
            />
            {draft ? (
              <button
                type="button"
                onClick={() => {
                  setDraft('')
                  setSubmittedQuery('')
                  inputRef.current?.focus()
                }}
                className="rounded-full p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            ) : null}
            <Button
              type="submit"
              size="sm"
              className="h-8 rounded-full px-4 text-xs"
              disabled={!canSubmit || createProduct.isPending}
            >
              <Search className="mr-1 h-3.5 w-3.5" aria-hidden />
              Search
            </Button>
          </div>
        </form>

        <div
          className="max-h-[60vh] min-h-[200px] overflow-y-auto px-4 py-4"
          role="region"
          aria-label="Search results"
          aria-busy={isSearching}
          aria-live="polite"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={
                isSearching
                  ? 'loading'
                  : isError
                    ? 'error'
                    : results.length > 0
                      ? `results-${submittedQuery}`
                      : isSearchableQuery(submittedQuery)
                        ? `empty-${submittedQuery}`
                        : 'idle'
              }
              initial={motionEnabled ? { opacity: 0, y: 6 } : false}
              animate={{ opacity: 1, y: 0 }}
              exit={motionEnabled ? { opacity: 0, y: -6 } : undefined}
              transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
            >
              {renderStateView()}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="flex items-center justify-between border-t border-border/60 bg-muted/30 px-4 py-2 text-[11px] text-muted-foreground">
          <span>{EMPTY_FOOTNOTE}</span>
          {data ? (
            <span data-testid="search-meta">
              {data.cache_hit ? 'Cached' : `${data.latency_ms}ms`} ·{' '}
              {data.results.length} result{data.results.length === 1 ? '' : 's'}
            </span>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function IdleState({
  onExampleClick,
  onAddByUrl,
}: {
  onExampleClick: (example: string) => void
  onAddByUrl: () => void
}) {
  return (
    <div className="space-y-4" data-testid="search-idle">
      <p className="text-sm text-muted-foreground">
        Type a product name. We&apos;ll find it at Canadian retailers and let you
        track it with one click.
      </p>
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onExampleClick(example)}
            className={cn(
              'rounded-full border border-border/60 bg-background px-3 py-1.5 text-xs text-muted-foreground',
              'transition-all hover:border-border hover:bg-accent hover:text-foreground',
            )}
            data-testid="example-query"
          >
            {example}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={onAddByUrl}
        className={cn(
          'flex items-center gap-2 text-xs text-muted-foreground transition-colors hover:text-foreground',
        )}
        data-testid="add-by-url-link"
      >
        <Link2 className="h-3.5 w-3.5" aria-hidden />
        Have a specific URL instead? Add by URL
      </button>
    </div>
  )
}

function ErrorState({
  error,
  motionEnabled,
}: {
  error: unknown
  motionEnabled: boolean
}) {
  const message =
    error instanceof ApiError ? error.message : 'Search hit a snag — try again.'
  return (
    <div
      className={cn(
        'rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive',
        motionEnabled && 'animate-in fade-in-0',
      )}
      role="alert"
      data-testid="search-error"
    >
      {message}
    </div>
  )
}

function EmptyState({
  query,
  onAddByUrl,
}: {
  query: string
  onAddByUrl: () => void
}) {
  return (
    <div className="space-y-3 py-4 text-center" data-testid="search-empty">
      <p className="text-sm text-foreground">
        Nothing turned up for <span className="font-medium">{query}</span>.
      </p>
      <p className="text-xs text-muted-foreground">
        Try a different phrasing, or paste the product URL directly.
      </p>
      <Button
        variant="outline"
        size="sm"
        className="rounded-full"
        onClick={onAddByUrl}
      >
        <Link2 className="mr-1 h-3.5 w-3.5" aria-hidden />
        Add by URL
      </Button>
    </div>
  )
}

function ResultsList({
  items,
  pendingUrl,
  trackedUrl,
  onTrack,
  motionEnabled,
}: {
  items: SearchResultItem[]
  pendingUrl: string | null
  trackedUrl: string | null
  onTrack: (item: SearchResultItem) => void
  motionEnabled: boolean
}) {
  return (
    <motion.ul
      className="space-y-2"
      data-testid="search-results"
      initial={false}
      animate="visible"
      variants={{
        visible: motionEnabled
          ? { transition: { staggerChildren: STAGGER_DELAY_MS / 1000 } }
          : {},
      }}
    >
      <AnimatePresence initial={false}>
        {items.map((item) => (
          <SearchResultRow
            key={item.url}
            item={item}
            isPending={pendingUrl === item.url}
            isSucceeded={trackedUrl === item.url}
            onTrack={onTrack}
          />
        ))}
      </AnimatePresence>
    </motion.ul>
  )
}
