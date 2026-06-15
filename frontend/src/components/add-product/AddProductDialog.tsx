import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateProduct } from '@/hooks/useProducts'
import { CATEGORY_ORDER, categoryLabel, type ProductCategory } from '@/lib/categories'

interface AddProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddProductDialog({ open, onOpenChange }: AddProductDialogProps) {
  const [url, setUrl] = useState('')
  const [showManualCategory, setShowManualCategory] = useState(false)
  const [manualCategory, setManualCategory] = useState<ProductCategory>('clothing')
  const createProduct = useCreateProduct()

  const resetForm = () => {
    setUrl('')
    setShowManualCategory(false)
    setManualCategory('clothing')
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = url.trim()
    if (!trimmed || createProduct.isPending) return

    const payload = showManualCategory
      ? { url: trimmed, category: manualCategory }
      : { url: trimmed, category: 'auto' as const }

    createProduct.mutate(payload, {
      onSuccess: () => {
        onOpenChange(false)
        resetForm()
      },
    })
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !createProduct.isPending) {
          resetForm()
        }
        onOpenChange(next)
      }}
    >
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Product</DialogTitle>
            <DialogDescription>
              Paste a Canadian retailer product URL to start tracking. We&apos;ll automatically
              sort it into the right category — you can change it anytime.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="product-url">Product URL</Label>
              <Input
                id="product-url"
                type="url"
                placeholder="https://www.bestbuy.ca/..."
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                required
                disabled={createProduct.isPending}
              />
            </div>
            {showManualCategory ? (
              <div className="grid gap-2">
                <Label htmlFor="product-category">Category</Label>
                <Select
                  value={manualCategory}
                  onValueChange={(value) => setManualCategory(value as ProductCategory)}
                  disabled={createProduct.isPending}
                >
                  <SelectTrigger id="product-category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORY_ORDER.map((category) => (
                      <SelectItem key={category} value={category}>
                        {categoryLabel(category)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <Button
                type="button"
                variant="link"
                className="h-auto justify-start px-0 text-muted-foreground"
                onClick={() => setShowManualCategory(true)}
                disabled={createProduct.isPending}
              >
                Set category manually
              </Button>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createProduct.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createProduct.isPending || !url.trim()}>
              {createProduct.isPending ? 'Adding…' : 'Add'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
