"""Notification evaluation interfaces (PRD §7.5, §7.10)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, field_validator

_PAYLOAD_MAX_BYTES = 8 * 1024


class NotificationKind(str, Enum):
    PRICE_DROP = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    DISCOVERY_COMPLETE = "discovery_complete"
    NEEDS_INPUT = "needs_input"
    SCRAPE_FAILING = "scrape_failing"
    REVISIT_ON_SALE = "revisit_on_sale"
    REVISIT_STALE = "revisit_stale"


class NotificationProposal(BaseModel):
    user_id: UUID
    product_id: UUID | None = None
    listing_id: UUID | None = None
    type: NotificationKind
    payload: dict[str, Any] = {}

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(value, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _PAYLOAD_MAX_BYTES:
            raise ValueError(
                f"payload serialized size exceeds {_PAYLOAD_MAX_BYTES} bytes"
            )
        return value


class NotificationEvaluationContext(BaseModel):
    """Minimal snapshot inputs for notification evaluation.

    Placeholder dict[str, Any] fields will be tightened into typed snapshots in T3.4.
    """

    user_id: UUID
    product_id: UUID
    evaluated_at: datetime
    profile: dict[str, Any]
    product: dict[str, Any]
    listings: list[dict[str, Any]] = []
    recent_observations: list[Any] = []
    recent_notifications: list[dict[str, Any]] = []

    @field_validator("evaluated_at")
    @classmethod
    def validate_evaluated_at_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        return value


class NotificationEvaluator(Protocol):
    kind: NotificationKind

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        ...


class PriceDropEvaluator:
    kind = NotificationKind.PRICE_DROP

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class BackInStockEvaluator:
    kind = NotificationKind.BACK_IN_STOCK

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class ScrapeFailingEvaluator:
    kind = NotificationKind.SCRAPE_FAILING

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class RevisitOnSaleEvaluator:
    kind = NotificationKind.REVISIT_ON_SALE

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class RevisitStaleEvaluator:
    kind = NotificationKind.REVISIT_STALE

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class NullNotificationEvaluator:
    """Hard-off default; evaluate always returns []."""

    kind = NotificationKind.PRICE_DROP

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        return []


class RecordingNotificationEvaluator:
    """Test fake that records context and returns configured proposals."""

    def __init__(
        self,
        proposals: Sequence[NotificationProposal],
        *,
        kind: NotificationKind = NotificationKind.PRICE_DROP,
    ) -> None:
        self.kind = kind
        self._proposals = list(proposals)
        self.received: list[NotificationEvaluationContext] = []

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        self.received.append(ctx)
        return list(self._proposals)


class CompositeNotificationEvaluator:
    """Runs child evaluators sequentially and concatenates results."""

    kind = NotificationKind.PRICE_DROP

    def __init__(self, evaluators: Sequence[NotificationEvaluator]) -> None:
        self._evaluators = list(evaluators)

    def evaluate(
        self, ctx: NotificationEvaluationContext
    ) -> Sequence[NotificationProposal]:
        results: list[NotificationProposal] = []
        for evaluator in self._evaluators:
            results.extend(evaluator.evaluate(ctx))
        return results
