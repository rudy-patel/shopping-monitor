import { useEffect, useRef, useState } from 'react'
import { Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useUpdateProduct } from '@/hooks/useProducts'

interface ProductTitleFieldProps {
  productId: string
  title: string
}

export function ProductTitleField({ productId, title }: ProductTitleFieldProps) {
  const update = useUpdateProduct(productId)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)
  const inputRef = useRef<HTMLInputElement>(null)
  const skipBlurCommitRef = useRef(false)

  useEffect(() => {
    setDraft(title)
  }, [title])

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing])

  const cancel = () => {
    setDraft(title)
    setEditing(false)
  }

  const commit = () => {
    if (update.isPending) return

    const trimmed = draft.trim()
    if (!trimmed) {
      cancel()
      return
    }
    if (trimmed === title) {
      setEditing(false)
      return
    }
    update.mutate(
      { title: trimmed },
      {
        onSuccess: () => setEditing(false),
      },
    )
  }

  if (editing) {
    return (
      <>
        <h1 className="sr-only">{title}</h1>
        <Input
          ref={inputRef}
          id="product-title"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={() => {
            if (skipBlurCommitRef.current) {
              skipBlurCommitRef.current = false
              return
            }
            commit()
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              skipBlurCommitRef.current = true
              commit()
            }
            if (event.key === 'Escape') {
              event.preventDefault()
              skipBlurCommitRef.current = true
              cancel()
            }
          }}
          disabled={update.isPending}
          className="text-xl font-semibold tracking-tight md:text-2xl"
          aria-label="Product name"
        />
      </>
    )
  }

  return (
    <div className="flex items-start gap-2">
      <h1 className="min-w-0 flex-1 text-xl font-semibold tracking-tight md:text-2xl">
        {title}
      </h1>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-8 shrink-0 text-muted-foreground"
        onClick={() => setEditing(true)}
        aria-label="Rename product"
      >
        <Pencil className="mr-1 h-4 w-4" aria-hidden />
        Rename
      </Button>
    </div>
  )
}
