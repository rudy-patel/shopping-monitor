import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { ApiError } from '@/lib/api'
import {
  acceptListing,
  createProduct,
  deleteListing,
  deleteProduct,
  getProduct,
  listProducts,
  productQueryKey,
  productsQueryKey,
  isProductListQueryKey,
  refreshProduct,
  rejectListing,
  selectVariant,
  updateProduct,
  type CreateProductInput,
  type ProductDetail,
  type ProductFilters,
  type ProductSummary,
  type UpdateProductInput,
} from '@/lib/products'

const PRODUCT_DETAIL_POLL_MS = 3_000
const PRODUCT_LIST_POLL_MS = 5_000

function isDiscoveryInFlight(status: ProductSummary['discovery_status'] | undefined) {
  return status === 'pending' || status === 'running'
}

export function productDetailRefetchInterval(
  data: ProductDetail | undefined,
): number | false {
  if (!data) return false
  return isDiscoveryInFlight(data.discovery_status) ? PRODUCT_DETAIL_POLL_MS : false
}

export function productListRefetchInterval(
  items: ProductSummary[] | undefined,
): number | false {
  if (!items?.some((product) => isDiscoveryInFlight(product.discovery_status))) {
    return false
  }
  return PRODUCT_LIST_POLL_MS
}

function rollbackListCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  snapshots: [readonly unknown[], ProductSummary[] | undefined][],
) {
  for (const [key, data] of snapshots) {
    queryClient.setQueryData(key, data)
  }
}

function snapshotListCaches(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.getQueriesData<ProductSummary[]>({
    predicate: (query) => isProductListQueryKey(query.queryKey),
  })
}

function updateListCache(
  queryClient: ReturnType<typeof useQueryClient>,
  updater: (items: ProductSummary[]) => ProductSummary[],
) {
  queryClient.setQueriesData<ProductSummary[]>(
    {
      predicate: (query) => isProductListQueryKey(query.queryKey),
    },
    (current: ProductSummary[] | undefined) =>
      Array.isArray(current) ? updater(current) : current,
  )
}

const ACTIVE_FILTERS: ProductFilters = { status: 'active' }

export function useProducts(filters: ProductFilters = ACTIVE_FILTERS) {
  return useQuery<ProductSummary[]>({
    queryKey: productsQueryKey(filters),
    queryFn: () => listProducts(filters),
    refetchInterval: (query) => productListRefetchInterval(query.state.data),
  })
}

export function useProduct(id: string | undefined) {
  const queryClient = useQueryClient()
  const wasInFlightRef = useRef(false)
  const listingCountAtStartRef = useRef<number | undefined>()

  useEffect(() => {
    wasInFlightRef.current = false
    listingCountAtStartRef.current = undefined
  }, [id])

  const query = useQuery<ProductDetail>({
    queryKey: productQueryKey(id ?? ''),
    queryFn: () => {
      if (!id) throw new Error('Product id is required')
      return getProduct(id)
    },
    enabled: Boolean(id),
    refetchInterval: (query) => productDetailRefetchInterval(query.state.data),
  })

  useEffect(() => {
    const data = query.data
    if (!data) return

    const inFlight = isDiscoveryInFlight(data.discovery_status)
    if (inFlight) {
      wasInFlightRef.current = true
      if (listingCountAtStartRef.current === undefined) {
        listingCountAtStartRef.current = data.listing_count
      }
      return
    }

    if (
      wasInFlightRef.current &&
      data.discovery_status === 'complete' &&
      listingCountAtStartRef.current !== undefined &&
      listingCountAtStartRef.current !== data.listing_count
    ) {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    }

    wasInFlightRef.current = false
    listingCountAtStartRef.current = undefined
  }, [query.data, queryClient])

  return query
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (input: CreateProductInput) => createProduct(input),
    onSuccess: (product) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      if (product.status === 'needs_input') {
        navigate(`/products/${product.id}/variants`)
      } else {
        navigate(`/products/${product.id}`)
      }
    },
    onError: (error) => {
      const message = error instanceof ApiError ? error.message : 'Could not add product'
      toast.error(message)
    },
  })
}

export function useUpdateProduct(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (patch: UpdateProductInput) => updateProduct(id, patch),
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: productQueryKey(id) })
      const previousDetail = queryClient.getQueryData<ProductDetail>(productQueryKey(id))
      const previousLists = snapshotListCaches(queryClient)

      if (previousDetail) {
        const optimistic: ProductDetail = {
          ...previousDetail,
          ...patch,
          category_source: patch.category ? 'manual' : previousDetail.category_source,
        }
        queryClient.setQueryData(productQueryKey(id), optimistic)
        updateListCache(queryClient, (items) =>
          items.map((item) =>
            item.id === id
              ? {
                  ...item,
                  ...patch,
                  category_source: patch.category ? 'manual' : item.category_source,
                }
              : item,
          ),
        )
      }

      return { previousDetail, previousLists }
    },
    onError: (_error, _patch, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(productQueryKey(id), context.previousDetail)
      }
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not save changes')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(id) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useDeleteProduct({ redirectTo = '/' }: { redirectTo?: string | null } = {}) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: deleteProduct,
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({
        predicate: (query) => isProductListQueryKey(query.queryKey),
      })
      const previousLists = snapshotListCaches(queryClient)
      updateListCache(queryClient, (items) => items.filter((item) => item.id !== deletedId))
      return { previousLists, deletedId }
    },
    onSuccess: (_result, deletedId) => {
      queryClient.removeQueries({ queryKey: productQueryKey(deletedId) })
      if (redirectTo !== null) {
        navigate(redirectTo)
      }
      toast('Product deleted')
    },
    onError: (_error, _deletedId, context) => {
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not delete product')
    },
    onSettled: (_result, _error, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.removeQueries({ queryKey: productQueryKey(deletedId) })
    },
  })
}

export function useRefreshProduct(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => refreshProduct(id),
    onSuccess: (product) => {
      queryClient.setQueryData(productQueryKey(id), product)
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 429) {
        toast('Refresh is on cooldown. Try again in about an hour.')
        return
      }
      toast.error('Could not refresh product')
    },
  })
}

export function useSelectVariant(id: string) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (variantAttributes: Record<string, string>) =>
      selectVariant(id, variantAttributes),
    onSuccess: (product) => {
      queryClient.setQueryData(productQueryKey(id), product)
      queryClient.invalidateQueries({ queryKey: ['products'] })
      navigate(`/products/${id}`)
    },
    onError: () => {
      toast.error('Could not select variant')
    },
  })
}

export function useArchiveProduct(id: string) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: () => updateProduct(id, { status: 'archived' }),
    onMutate: async () => {
      await queryClient.cancelQueries({
        predicate: (query) => isProductListQueryKey(query.queryKey),
      })
      const previousLists = snapshotListCaches(queryClient)
      updateListCache(queryClient, (items) => items.filter((item) => item.id !== id))
      return { previousLists }
    },
    onSuccess: () => {
      toast('Product archived')
      navigate('/history')
    },
    onError: (_error, _vars, context) => {
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not archive product')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(id) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useRestoreProduct(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => updateProduct(id, { status: 'active' }),
    onMutate: async () => {
      await queryClient.cancelQueries({
        predicate: (query) => isProductListQueryKey(query.queryKey),
      })
      const previousLists = snapshotListCaches(queryClient)
      updateListCache(queryClient, (items) => items.filter((item) => item.id !== id))
      return { previousLists }
    },
    onSuccess: (product) => {
      queryClient.setQueryData(productQueryKey(id), product)
      toast('Product restored to your list')
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (_error, _vars, context) => {
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error('Could not restore product')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(id) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

function applyDetailToListSummary(
  item: ProductSummary,
  detail: ProductDetail,
): ProductSummary {
  return {
    ...item,
    best_price_cents: detail.best_price_cents,
    best_retailer_slug: detail.best_retailer_slug,
    trend: detail.trend,
    listing_count: detail.listing_count,
    needs_review_count: detail.needs_review_count,
    last_scraped_at: detail.last_scraped_at,
  }
}

type ListingMutationContext = {
  previousDetail?: ProductDetail
  previousLists: [readonly unknown[], ProductSummary[] | undefined][]
}

function useListingDetailMutation(
  productId: string,
  mutationFn: (listingId: string) => Promise<ProductDetail>,
  {
    optimisticDetail,
    optimisticSummary,
    errorMessage,
  }: {
    optimisticDetail: (detail: ProductDetail, listingId: string) => ProductDetail
    optimisticSummary: (summary: ProductSummary, detail: ProductDetail) => ProductSummary
    errorMessage: string
  },
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn,
    onMutate: async (listingId): Promise<ListingMutationContext> => {
      await queryClient.cancelQueries({ queryKey: productQueryKey(productId) })
      const previousDetail = queryClient.getQueryData<ProductDetail>(productQueryKey(productId))
      const previousLists = snapshotListCaches(queryClient)

      if (previousDetail) {
        const optimistic = optimisticDetail(previousDetail, listingId)
        queryClient.setQueryData(productQueryKey(productId), optimistic)
        updateListCache(queryClient, (items) =>
          items.map((item) =>
            item.id === productId ? optimisticSummary(item, optimistic) : item,
          ),
        )
      }

      return { previousDetail, previousLists }
    },
    onSuccess: (detail) => {
      queryClient.setQueryData(productQueryKey(productId), detail)
      updateListCache(queryClient, (items) =>
        items.map((item) =>
          item.id === productId ? applyDetailToListSummary(item, detail) : item,
        ),
      )
    },
    onError: (_error, _listingId, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(productQueryKey(productId), context.previousDetail)
      }
      rollbackListCaches(queryClient, context?.previousLists ?? [])
      toast.error(errorMessage)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: productQueryKey(productId) })
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useAcceptListing(productId: string) {
  return useListingDetailMutation(productId, (listingId) => acceptListing(productId, listingId), {
    optimisticDetail: (detail, listingId) => {
      const listings = detail.listings.map((listing) =>
        listing.id === listingId ? { ...listing, review_status: 'accepted' } : listing,
      )
      return {
        ...detail,
        listings,
        needs_review_count: listings.filter((l) => l.review_status === 'needs_review').length,
      }
    },
    optimisticSummary: (item, detail) => ({
      ...item,
      needs_review_count: detail.needs_review_count,
    }),
    errorMessage: 'Could not accept listing',
  })
}

export function useRejectListing(productId: string) {
  return useListingDetailMutation(productId, (listingId) => rejectListing(productId, listingId), {
    optimisticDetail: (detail, listingId) => {
      const listings = detail.listings.map((listing) =>
        listing.id === listingId ? { ...listing, review_status: 'rejected' } : listing,
      )
      return {
        ...detail,
        listings,
        needs_review_count: listings.filter((l) => l.review_status === 'needs_review').length,
      }
    },
    optimisticSummary: (item, detail) => ({
      ...item,
      needs_review_count: detail.needs_review_count,
    }),
    errorMessage: 'Could not reject listing',
  })
}

export function useDeleteListing(productId: string) {
  return useListingDetailMutation(productId, (listingId) => deleteListing(productId, listingId), {
    optimisticDetail: (detail, listingId) => {
      const listings = detail.listings.filter((listing) => listing.id !== listingId)
      return {
        ...detail,
        listings,
        listing_count: listings.length,
      }
    },
    optimisticSummary: (item, detail) => ({
      ...item,
      listing_count: detail.listing_count,
    }),
    errorMessage: 'Could not remove listing',
  })
}
