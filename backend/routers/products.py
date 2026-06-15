"""Product API endpoints (T2.5)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.auth import CurrentUser, get_current_user
from services.discovery import run_discovery_for_product
from services.product_service import (
    ProductCategory,
    ProductStatus,
    accept_listing,
    create_product,
    delete_listing,
    delete_product,
    get_product,
    list_products,
    refresh_product,
    reject_listing,
    reorder_dashboard_products,
    select_variant,
    update_product,
)

router = APIRouter(prefix="/api", tags=["products"])

TrendDirection = Literal["down", "same", "up"]
CategoryInput = Literal["auto", "clothing", "shoes", "home", "tech", "other"]
MAX_PRODUCT_TITLE_LEN = 200


class TrendChip(BaseModel):
    direction: TrendDirection
    delta_pct: float | None
    days_of_data: int
    label: str


class ListingResponse(BaseModel):
    id: UUID
    retailer_slug: str
    url: str
    variant_attributes: dict[str, str]
    available_variants: list[dict] | None = None
    is_primary: bool
    review_status: str
    last_known_price_cents: int | None
    is_in_stock: bool | None
    last_scraped_at: str | None
    scrape_status: str | None
    match_confidence: float | None
    review_title: str | None = None
    review_image_url: str | None = None
    review_reason: str | None = None


class ProductSummary(BaseModel):
    id: UUID
    title: str
    brand: str | None
    image_url: str | None
    category: ProductCategory
    category_source: str
    status: ProductStatus
    notification_threshold_pct: int | None
    notifications_enabled: bool
    discovery_status: str
    last_refresh_at: str | None
    last_user_interaction_at: str | None
    created_at: str
    updated_at: str
    best_price_cents: int | None
    best_retailer_slug: str | None
    trend: TrendChip
    listing_count: int
    effective_threshold_pct: int
    last_scraped_at: str | None
    needs_review_count: int = 0
    dashboard_sort_order: int | None = None


class PriceHistoryPoint(BaseModel):
    observed_on: str
    price_cents: int


class ProductDetail(ProductSummary):
    listings: list[ListingResponse]
    price_history_30d: list[PriceHistoryPoint] = Field(default_factory=list)


class DiscoverySeedEntry(BaseModel):
    """One pre-vetted candidate from the search flow that should skip the LLM discover() call."""

    retailer_slug: str
    url: str


class ProductCreateRequest(BaseModel):
    url: str
    category: CategoryInput | None = "auto"
    discovery_seed: list[DiscoverySeedEntry] | None = None


class ProductUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=MAX_PRODUCT_TITLE_LEN)
    category: ProductCategory | None = None
    notification_threshold_pct: int | None = Field(default=None, ge=1, le=95)
    notifications_enabled: bool | None = None
    status: Literal["active", "archived"] | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped


class SelectVariantRequest(BaseModel):
    variant_attributes: dict[str, str]


class DashboardReorderEntry(BaseModel):
    id: UUID
    dashboard_sort_order: int = Field(ge=0)


class DashboardReorderRequest(BaseModel):
    items: list[DashboardReorderEntry] = Field(min_length=1)


@router.post("/products", response_model=ProductDetail, status_code=201)
async def post_product(
    body: ProductCreateRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    category = None if body.category in (None, "auto") else body.category
    detail = create_product(user_id=user.user_id, url=body.url, category=category)
    seed = (
        [(entry.retailer_slug, entry.url) for entry in body.discovery_seed]
        if body.discovery_seed
        else None
    )
    background_tasks.add_task(
        run_discovery_for_product,
        UUID(detail["id"]),
        seed=seed,
    )
    return ProductDetail.model_validate(detail)


@router.get("/products", response_model=list[ProductSummary])
async def get_products(
    status: ProductStatus | None = Query(default="active"),
    category: ProductCategory | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
) -> list[ProductSummary]:
    rows = list_products(user_id=user.user_id, status=status, category=category)
    return [ProductSummary.model_validate(row) for row in rows]


@router.put("/products/dashboard-order", status_code=204)
async def put_dashboard_order(
    body: DashboardReorderRequest,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    reorder_dashboard_products(
        user_id=user.user_id,
        items=[entry.model_dump() for entry in body.items],
    )


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product_by_id(
    product_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    detail = get_product(user_id=user.user_id, product_id=product_id)
    return ProductDetail.model_validate(detail)


@router.patch("/products/{product_id}", response_model=ProductDetail)
async def patch_product(
    product_id: UUID,
    body: ProductUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    detail = update_product(user_id=user.user_id, product_id=product_id, patch=patch)
    return ProductDetail.model_validate(detail)


@router.delete("/products/{product_id}", status_code=204)
async def delete_product_by_id(
    product_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    delete_product(user_id=user.user_id, product_id=product_id)


@router.post("/products/{product_id}/refresh", response_model=ProductDetail)
async def post_refresh_product(
    product_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    detail = refresh_product(user_id=user.user_id, product_id=product_id)
    return ProductDetail.model_validate(detail)


@router.post("/products/{product_id}/select-variant", response_model=ProductDetail)
async def post_select_variant(
    product_id: UUID,
    body: SelectVariantRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    detail = select_variant(
        user_id=user.user_id,
        product_id=product_id,
        variant_attributes=body.variant_attributes,
    )
    return ProductDetail.model_validate(detail)


@router.post(
    "/products/{product_id}/listings/{listing_id}/accept",
    response_model=ProductDetail,
)
async def post_accept_listing(
    product_id: UUID,
    listing_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    detail = accept_listing(
        user_id=user.user_id,
        product_id=product_id,
        listing_id=listing_id,
    )
    return ProductDetail.model_validate(detail)


@router.post(
    "/products/{product_id}/listings/{listing_id}/reject",
    response_model=ProductDetail,
)
async def post_reject_listing(
    product_id: UUID,
    listing_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    detail = reject_listing(
        user_id=user.user_id,
        product_id=product_id,
        listing_id=listing_id,
    )
    return ProductDetail.model_validate(detail)


@router.delete(
    "/products/{product_id}/listings/{listing_id}",
    response_model=ProductDetail,
)
async def delete_listing_by_id(
    product_id: UUID,
    listing_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ProductDetail:
    detail = delete_listing(
        user_id=user.user_id,
        product_id=product_id,
        listing_id=listing_id,
    )
    return ProductDetail.model_validate(detail)
