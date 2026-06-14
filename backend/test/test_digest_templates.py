"""Digest template unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from services.digest_templates import (
    DIGEST_SUBJECT,
    build_digest_email,
    build_digest_entry,
    notification_deep_link,
    notification_summary,
    render_digest_html,
    render_digest_text,
)
from services.notifications import NotificationKind


def _row(
    *,
    notification_type: str,
    product_id: str | None = None,
    payload: dict | None = None,
) -> dict:
    return {
        "id": str(uuid4()),
        "type": notification_type,
        "product_id": product_id,
        "payload": payload or {},
        "created_at": datetime(2026, 6, 14, 12, 0, tzinfo=UTC).isoformat(),
    }


def test_digest_subject_is_locked():
    assert DIGEST_SUBJECT == "Your Shopping Monitor digest"


def test_price_drop_summary_uses_cad():
    summary = notification_summary(
        notification_type=NotificationKind.PRICE_DROP,
        product_title="Widget",
        payload={"old_price_cents": 10000, "new_price_cents": 8000},
    )
    assert summary == "Widget dropped from $100.00 to $80.00."


def test_back_in_stock_summary_uses_retailer_label():
    summary = notification_summary(
        notification_type=NotificationKind.BACK_IN_STOCK,
        product_title="Widget",
        payload={"retailer_slug": "bestbuy_ca"},
    )
    assert summary == "Widget is back in stock at Best Buy Canada."


def test_revisit_types_link_to_notifications():
    for kind in (NotificationKind.REVISIT_ON_SALE, NotificationKind.REVISIT_STALE):
        link = notification_deep_link(
            app_base_url="http://localhost:3000",
            notification_type=kind,
            product_id=uuid4(),
        )
        assert link == "http://localhost:3000/notifications"


def test_needs_input_links_to_variant_picker():
    product_id = uuid4()
    link = notification_deep_link(
        app_base_url="http://localhost:3000",
        notification_type=NotificationKind.NEEDS_INPUT,
        product_id=product_id,
    )
    assert link == f"http://localhost:3000/products/{product_id}/variants"


def test_build_digest_entry_and_rendered_bodies():
    product_id = str(uuid4())
    row = _row(
        notification_type="scrape_failing",
        product_id=product_id,
        payload={},
    )
    entry = build_digest_entry(
        row=row,
        product_title="Switch 2",
        app_base_url="http://localhost:3000",
    )
    email = build_digest_email(to_email="user@example.com", entries=[entry])

    assert "Switch 2" in email.text_body
    assert f"/products/{product_id}" in email.text_body
    assert "Switch 2" in email.html_body
    assert "View in app" in render_digest_html([entry])
    assert entry.summary in render_digest_text([entry])


def test_discovery_complete_copy_with_needs_review():
    summary = notification_summary(
        notification_type=NotificationKind.DISCOVERY_COMPLETE,
        product_title="Camera",
        payload={"auto_added_count": 1, "needs_review_count": 2},
    )
    assert summary == "Found 3 matches for Camera. 2 need your review."
