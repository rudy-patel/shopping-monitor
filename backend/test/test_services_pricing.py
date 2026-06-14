"""Pricing and trend helper tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from services.pricing import (
    DEFAULT_NOTIFICATION_THRESHOLD_PCT,
    ELIGIBLE_REVIEW_STATUSES,
    MIN_TREND_HISTORY_DAYS,
    PRICE_DROP_DEBOUNCE_HOURS,
    REVISIT_DEBOUNCE_DAYS,
    REVISIT_ON_SALE_PCT,
    REVISIT_PRICE_DROP_OVERLAP_DAYS,
    TREND_DEADBAND_PCT,
    TREND_WINDOW_DAYS,
    ListingDailyObservation,
    TrendDirection,
    compute_trend,
    is_eligible_for_pricing,
    is_revisit_on_sale_eligible,
    price_drop_pct,
    product_daily_minimum,
    should_fire_price_drop,
)


def _obs(
    *,
    observed_on: date,
    price_cents: int = 10000,
    is_in_stock: bool = True,
    review_status: str = "accepted",
    is_primary: bool = False,
    listing_id=None,
) -> ListingDailyObservation:
    return ListingDailyObservation(
        listing_id=listing_id or uuid4(),
        observed_on=observed_on,
        price_cents=price_cents,
        is_in_stock=is_in_stock,
        review_status=review_status,  # type: ignore[arg-type]
        is_primary=is_primary,
    )


def test_is_eligible_for_pricing():
    today = date(2026, 6, 14)
    assert is_eligible_for_pricing(_obs(observed_on=today, is_primary=True)) is True
    assert (
        is_eligible_for_pricing(
            _obs(observed_on=today, review_status="auto_added")
        )
        is True
    )
    assert (
        is_eligible_for_pricing(_obs(observed_on=today, review_status="accepted"))
        is True
    )
    assert (
        is_eligible_for_pricing(
            _obs(observed_on=today, review_status="needs_review")
        )
        is False
    )
    assert (
        is_eligible_for_pricing(_obs(observed_on=today, review_status="rejected"))
        is False
    )
    assert (
        is_eligible_for_pricing(
            _obs(observed_on=today, is_primary=True, is_in_stock=False)
        )
        is False
    )


def test_product_daily_minimum_picks_lowest_eligible_per_day():
    day1 = date(2026, 6, 10)
    day2 = date(2026, 6, 11)
    observations = [
        _obs(observed_on=day1, price_cents=10000, is_primary=True),
        _obs(observed_on=day1, price_cents=9000, review_status="accepted"),
        _obs(observed_on=day2, price_cents=8000, is_primary=True),
        _obs(observed_on=day2, price_cents=7000, review_status="needs_review"),
    ]
    assert product_daily_minimum(observations) == {day1: 9000, day2: 8000}


def test_compute_trend_empty_observations():
    result = compute_trend([], today=date(2026, 6, 14))
    assert result.direction == TrendDirection.SAME
    assert result.delta_pct is None
    assert result.days_of_data == 0


def test_compute_trend_insufficient_history():
    today = date(2026, 6, 14)
    observations = [
        _obs(observed_on=today - timedelta(days=i), price_cents=10000, is_primary=True)
        for i in range(6)
    ]
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.SAME
    assert result.delta_pct is None
    assert result.days_of_data == 6


def test_compute_trend_down_after_seven_days():
    today = date(2026, 6, 14)
    observations = [
        _obs(observed_on=today - timedelta(days=30), price_cents=10000, is_primary=True),
        *[
            _obs(
                observed_on=today - timedelta(days=i),
                price_cents=9000,
                is_primary=True,
            )
            for i in range(6)
        ],
    ]
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.DOWN
    assert result.delta_pct == Decimal("-0.1000")
    assert result.days_of_data == 7


def _trend_observations(
    today: date,
    *,
    span_days: int,
    price_cents: int,
) -> list[ListingDailyObservation]:
    return [
        _obs(
            observed_on=today - timedelta(days=i),
            price_cents=price_cents,
            is_primary=True,
        )
        for i in range(span_days + 1)
    ]


def test_compute_trend_flat_30_days():
    today = date(2026, 6, 14)
    observations = _trend_observations(today, span_days=30, price_cents=10000)
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.SAME
    assert result.delta_pct == Decimal("0.0000")
    assert result.days_of_data == 31


def test_compute_trend_deadband_inclusive_down():
    today = date(2026, 6, 14)
    observations = _trend_observations(today, span_days=30, price_cents=10000)
    observations[0] = _obs(observed_on=today, price_cents=9700, is_primary=True)
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.DOWN
    assert result.delta_pct == Decimal("-0.0300")


def test_compute_trend_deadband_inclusive_up():
    today = date(2026, 6, 14)
    observations = _trend_observations(today, span_days=30, price_cents=10000)
    observations[0] = _obs(observed_on=today, price_cents=10300, is_primary=True)
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.UP
    assert result.delta_pct == Decimal("0.0300")


def test_compute_trend_within_deadband_same():
    today = date(2026, 6, 14)
    observations = _trend_observations(today, span_days=30, price_cents=10000)
    observations[0] = _obs(observed_on=today, price_cents=9800, is_primary=True)
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.SAME
    assert result.delta_pct == Decimal("-0.0200")


def test_compute_trend_anchor_falls_back_to_nearest_earlier_date():
    today = date(2026, 6, 14)
    observations = _trend_observations(today, span_days=30, price_cents=10000)
    observations[0] = _obs(observed_on=today, price_cents=9000, is_primary=True)
    observations[-1] = _obs(
        observed_on=today - timedelta(days=32),
        price_cents=10000,
        is_primary=True,
    )
    result = compute_trend(observations, today=today)
    assert result.direction == TrendDirection.DOWN
    assert result.delta_pct == Decimal("-0.1000")


def test_price_drop_pct():
    assert price_drop_pct(baseline_cents=10000, current_cents=8000) == Decimal("0.2000")
    with pytest.raises(ValueError):
        price_drop_pct(baseline_cents=0, current_cents=100)


def test_should_fire_price_drop():
    assert (
        should_fire_price_drop(
            baseline_cents=10000, current_cents=8000, threshold_pct=20
        )
        is True
    )
    assert (
        should_fire_price_drop(
            baseline_cents=10000, current_cents=8000, threshold_pct=25
        )
        is False
    )
    assert (
        should_fire_price_drop(
            baseline_cents=10000, current_cents=9900, threshold_pct=1
        )
        is True
    )


def test_is_revisit_on_sale_eligible():
    baseline = 10000
    assert is_revisit_on_sale_eligible(baseline_cents=baseline, current_cents=8500)
    assert not is_revisit_on_sale_eligible(
        baseline_cents=baseline, current_cents=8501
    )
    assert is_revisit_on_sale_eligible(baseline_cents=baseline, current_cents=5000)


def test_exported_constants():
    assert TREND_WINDOW_DAYS == 30
    assert TREND_DEADBAND_PCT == Decimal("0.03")
    assert MIN_TREND_HISTORY_DAYS == 7
    assert DEFAULT_NOTIFICATION_THRESHOLD_PCT == 20
    assert REVISIT_ON_SALE_PCT == Decimal("0.15")
    assert PRICE_DROP_DEBOUNCE_HOURS == 24
    assert REVISIT_DEBOUNCE_DAYS == 30
    assert REVISIT_PRICE_DROP_OVERLAP_DAYS == 7
    assert ELIGIBLE_REVIEW_STATUSES == frozenset({"auto_added", "accepted"})
