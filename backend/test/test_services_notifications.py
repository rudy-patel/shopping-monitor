"""NotificationEvaluator interface tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from services.notifications import (
    BackInStockEvaluator,
    CompositeNotificationEvaluator,
    NotificationEvaluationContext,
    NotificationKind,
    NotificationProposal,
    NullNotificationEvaluator,
    PriceDropEvaluator,
    RecordingNotificationEvaluator,
    RevisitOnSaleEvaluator,
    RevisitStaleEvaluator,
    ScrapeFailingEvaluator,
)


def _ctx() -> NotificationEvaluationContext:
    return NotificationEvaluationContext(
        user_id=uuid4(),
        product_id=uuid4(),
        evaluated_at=datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc),
        profile={},
        product={},
    )


def test_null_evaluator_returns_empty():
    assert NullNotificationEvaluator().evaluate(_ctx()) == []


def test_recording_evaluator_returns_proposals_and_records_context():
    ctx = _ctx()
    proposal = NotificationProposal(
        user_id=ctx.user_id,
        product_id=ctx.product_id,
        type=NotificationKind.PRICE_DROP,
    )
    evaluator = RecordingNotificationEvaluator([proposal])
    result = evaluator.evaluate(ctx)
    assert result == [proposal]
    assert evaluator.received == [ctx]


@pytest.mark.parametrize(
    ("evaluator_cls", "expected_kind"),
    [
        (PriceDropEvaluator, NotificationKind.PRICE_DROP),
        (BackInStockEvaluator, NotificationKind.BACK_IN_STOCK),
        (ScrapeFailingEvaluator, NotificationKind.SCRAPE_FAILING),
        (RevisitOnSaleEvaluator, NotificationKind.REVISIT_ON_SALE),
        (RevisitStaleEvaluator, NotificationKind.REVISIT_STALE),
    ],
)
def test_per_kind_stubs_return_empty_and_expose_kind(evaluator_cls, expected_kind):
    evaluator = evaluator_cls()
    assert evaluator.evaluate(_ctx()) == []
    assert evaluator.kind == expected_kind


def test_composite_evaluator_concatenates_in_order():
    ctx = _ctx()
    proposal_a = NotificationProposal(
        user_id=ctx.user_id,
        type=NotificationKind.PRICE_DROP,
    )
    proposal_b = NotificationProposal(
        user_id=ctx.user_id,
        type=NotificationKind.BACK_IN_STOCK,
    )
    composite = CompositeNotificationEvaluator(
        [
            RecordingNotificationEvaluator([proposal_a]),
            RecordingNotificationEvaluator([proposal_b]),
        ]
    )
    assert composite.evaluate(ctx) == [proposal_a, proposal_b]


def test_notification_kind_matches_migration_constraint():
    expected = {
        "price_drop",
        "back_in_stock",
        "discovery_complete",
        "needs_input",
        "scrape_failing",
        "revisit_on_sale",
        "revisit_stale",
    }
    actual = {member.value for member in NotificationKind}
    assert actual == expected


def test_notification_proposal_rejects_over_cap_payload():
    oversized = {"data": "x" * (8 * 1024)}
    serialized = json.dumps(oversized, separators=(",", ":"))
    assert len(serialized.encode("utf-8")) > 8 * 1024
    with pytest.raises(ValidationError, match="payload"):
        NotificationProposal(
            user_id=uuid4(),
            type=NotificationKind.PRICE_DROP,
            payload=oversized,
        )
