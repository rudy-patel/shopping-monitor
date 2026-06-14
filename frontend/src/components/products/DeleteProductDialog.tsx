import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useDeleteProduct } from '@/hooks/useProducts'

interface DeleteProductDialogProps {
  productId: string
  productTitle: string
  open: boolean
  onOpenChange: (open: boolean) => void
  redirectTo?: string | null
}

export function DeleteProductDialog({
  productId,
  productTitle,
  open,
  onOpenChange,
  redirectTo = '/',
}: DeleteProductDialogProps) {
  const remove = useDeleteProduct({ redirectTo })

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete product</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently removes {productTitle} and all tracked prices.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={remove.isPending}
            onClick={() => remove.mutate(productId)}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
