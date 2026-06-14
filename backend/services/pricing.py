"""Product price/trend helpers (PRD §7.4, §7.5, §7.10)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

TREND_WINDOW_DAYS = 30
TREND_DEADBAND_PCT = Decimal("0.03")
MIN_TREND_HISTORY_DAYS = 7
DEFAULT_NOTIFICATION_THRESHOLD_PCT = 20
REVISIT_ON_SALE_PCT = Decimal("0.15")
PRICE_DROP_DEBOUNCE_HOURS = 24
REVISIT_DEBOUNCE_DAYS = 30
REVISIT_PRICE_DROP_OVERLAP_DAYS = 7
ELIGIBLE_REVIEW_STATUSES: frozenset[str] = frozenset({"auto_added", "accepted"})

__all__ = [
    "DEFAULT_NOTIFICATION_THRESHOLD_PCT",
    "ELIGIBLE_REVIEW_STATUSES",
    "ListingDailyObservation",
    "MIN_TREND_HISTORY_DAYS",
    "PRICE_DROP_DEBOUNCE_HOURS",
    "REVISIT_DEBOUNCE_DAYS",
    "REVISIT_ON_SALE_PCT",
    "REVISIT_PRICE_DROP_OVERLAP_DAYS",
    "TREND_DEADBAND_PCT",
    "TREND_WINDOW_DAYS",
    "TrendDirection",
    "TrendResult",
    "compute_trend",
    "is_eligible_for_pricing",
    "is_revisit_on_sale_eligible",
    "price_drop_pct",
    "product_daily_minimum",
    "should_fire_price_drop",
]


class ListingDailyObservation(BaseModel):
    listing_id: UUID
    observed_on: date
    price_cents: int
    is_in_stock: bool
    review_status: Literal["auto_added", "needs_review", "accepted", "rejected"]
    is_primary: bool

    @field_validator("price_cents")
    @classmethod
    def validate_price_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("price_cents must be >= 0")
        return value


class TrendDirection(str, Enum):
    DOWN = "down"
    SAME = "same"
    UP = "up"


class TrendResult(BaseModel):
    direction: TrendDirection
    delta_pct: Decimal | None
    days_of_data: int


def is_eligible_for_pricing(obs: ListingDailyObservation) -> bool:
    """Eligible = (is_primary OR review_status in ELIGIBLE_REVIEW_STATUSES) AND is_in_stock."""
    if not obs.is_in_stock:
        return False
    return obs.is_primary or obs.review_status in ELIGIBLE_REVIEW_STATUSES


def product_daily_minimum(
    observations: Iterable[ListingDailyObservation],
) -> dict[date, int]:
    """Per-day min price across eligible observations only."""
    daily: dict[date, int] = {}
    for obs in observations:
        if not is_eligible_for_pricing(obs):
            continue
        existing = daily.get(obs.observed_on)
        if existing is None or obs.price_cents < existing:
            daily[obs.observed_on] = obs.price_cents
    return daily


def _nearest_date_at_or_before(target: date, available: list[date]) -> date | None:
    candidates = [d for d in available if d <= target]
    if not candidates:
        return None
    return max(candidates)


def compute_trend(
    observations: Iterable[ListingDailyObservation],
    *,
    today: date,
    window_days: int = TREND_WINDOW_DAYS,
) -> TrendResult:
    """Compute product-level price trend with deadband logic."""
    daily_min = product_daily_minimum(observations)
    if not daily_min:
        return TrendResult(
            direction=TrendDirection.SAME,
            delta_pct=None,
            days_of_data=0,
        )

    window_start = today - timedelta(days=window_days)
    dates_in_window = [d for d in daily_min if window_start <= d <= today]
    days_of_data = len(dates_in_window)

    if days_of_data < MIN_TREND_HISTORY_DAYS:
        return TrendResult(
            direction=TrendDirection.SAME,
            delta_pct=None,
            days_of_data=days_of_data,
        )

    sorted_dates = sorted(daily_min.keys())
    price_today_date = _nearest_date_at_or_before(today, sorted_dates)
    price_past_date = _nearest_date_at_or_before(
        today - timedelta(days=window_days), sorted_dates
    )

    if price_today_date is None or price_past_date is None:
        return TrendResult(
            direction=TrendDirection.SAME,
            delta_pct=None,
            days_of_data=days_of_data,
        )

    price_today = Decimal(daily_min[price_today_date])
    price_past = Decimal(daily_min[price_past_date])

    if price_past == 0:
        return TrendResult(
            direction=TrendDirection.SAME,
            delta_pct=None,
            days_of_data=days_of_data,
        )

    delta_pct = ((price_today - price_past) / price_past).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_EVEN
    )

    if delta_pct <= -TREND_DEADBAND_PCT:
        direction = TrendDirection.DOWN
    elif delta_pct >= TREND_DEADBAND_PCT:
        direction = TrendDirection.UP
    else:
        direction = TrendDirection.SAME

    return TrendResult(
        direction=direction,
        delta_pct=delta_pct,
        days_of_data=days_of_data,
    )


def price_drop_pct(*, baseline_cents: int, current_cents: int) -> Decimal:
    """Returns (baseline - current) / baseline as a Decimal fraction."""
    if baseline_cents <= 0:
        raise ValueError("baseline_cents must be > 0")
    return (
        (Decimal(baseline_cents) - Decimal(current_cents)) / Decimal(baseline_cents)
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def should_fire_price_drop(
    *, baseline_cents: int, current_cents: int, threshold_pct: int
) -> bool:
    """True iff price_drop_pct(...) * 100 >= threshold_pct."""
    drop = price_drop_pct(baseline_cents=baseline_cents, current_cents=current_cents)
    return drop * 100 >= threshold_pct


def is_revisit_on_sale_eligible(
    *, baseline_cents: int, current_cents: int
) -> bool:
    """True iff price_drop_pct(...) >= REVISIT_ON_SALE_PCT."""
    return price_drop_pct(baseline_cents=baseline_cents, current_cents=current_cents) >= REVISIT_ON_SALE_PCT
