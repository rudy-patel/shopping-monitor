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
import { ADD_PRODUCT_CATEGORIES, type CategoryInput } from '@/lib/categories'

interface AddProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddProductDialog({ open, onOpenChange }: AddProductDialogProps) {
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState<CategoryInput>('auto')
  const createProduct = useCreateProduct()

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) return

    onOpenChange(false)
    setUrl('')
    setCategory('auto')
    createProduct.mutate({ url: trimmed, category })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Product</DialogTitle>
            <DialogDescription>
              Paste a Canadian retailer product URL to start tracking.
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
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="product-category">Category</Label>
              <Select value={category} onValueChange={(value) => setCategory(value as CategoryInput)}>
                <SelectTrigger id="product-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ADD_PRODUCT_CATEGORIES.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createProduct.isPending}>
              Add
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
