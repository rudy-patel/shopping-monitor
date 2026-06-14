"""MailService interface tests.

DigestEmail.to_email is str (not pydantic EmailStr) because email-validator is not
a runtime dependency in T1.5. T3.6 will swap to EmailStr when Resend lands.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from services.mail import DigestEmail, DigestNotificationEntry, NoOpMailService
from services.notifications import NotificationKind


def _sample_entry() -> DigestNotificationEntry:
    return DigestNotificationEntry(
        notification_id=uuid4(),
        type=NotificationKind.PRICE_DROP,
        product_id=uuid4(),
        product_title="Example Product",
        summary="Price dropped 20%",
        deep_link="https://app.example.com/products/abc",
        created_at=datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc),
    )


def _sample_email() -> DigestEmail:
    return DigestEmail(
        to_email="user@example.com",
        subject="Your daily digest",
        text_body="text",
        html_body="<p>html</p>",
        entries=[_sample_entry()],
    )


def test_noop_mail_service_initializes_empty():
    mail = NoOpMailService()
    assert mail.sent == []


def test_noop_mail_service_captures_send():
    mail = NoOpMailService()
    email = _sample_email()
    mail.send_digest(email)
    assert mail.sent == [email]


def test_noop_mail_service_multiple_sends():
    mail = NoOpMailService()
    first = _sample_email()
    second = _sample_email()
    mail.send_digest(first)
    mail.send_digest(second)
    assert mail.sent == [first, second]


def test_noop_mail_service_reset():
    mail = NoOpMailService()
    mail.send_digest(_sample_email())
    mail.reset()
    assert mail.sent == []


def test_digest_email_rejects_empty_entries():
    with pytest.raises(ValidationError, match="entries"):
        DigestEmail(
            to_email="user@example.com",
            subject="Digest",
            text_body="text",
            html_body="html",
            entries=[],
        )


@pytest.mark.parametrize("to_email", ["not-an-email", "@example.com", "user@"])
def test_digest_email_rejects_invalid_to_email(to_email: str):
    with pytest.raises(ValidationError, match="to_email"):
        DigestEmail(
            to_email=to_email,
            subject="Digest",
            text_body="text",
            html_body="html",
            entries=[_sample_entry()],
        )


def test_digest_notification_entry_round_trip():
    entry = _sample_entry()
    restored = DigestNotificationEntry.model_validate(entry.model_dump())
    assert restored == entry
