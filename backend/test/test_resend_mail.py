"""ResendMailService unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from core.settings import Settings
from services.factory import get_mail_service
from services.mail import DigestEmail, DigestNotificationEntry, MailServiceError, NoOpMailService
from services.notifications import NotificationKind
from services.resend_mail import ResendMailService


def _sample_email() -> DigestEmail:
    return DigestEmail(
        to_email="user@example.com",
        subject="Your Shopping Monitor digest",
        text_body="text",
        html_body="<p>html</p>",
        entries=[
            DigestNotificationEntry(
                notification_id=uuid4(),
                type=NotificationKind.PRICE_DROP,
                product_id=uuid4(),
                product_title="Example",
                summary="Price dropped",
                deep_link="http://localhost:3000/products/abc",
                created_at=datetime.now(UTC),
            )
        ],
    )


def test_resend_mail_service_sends_with_configured_from():
    settings = Settings(
        resend_api_key="re_test",
        resend_from_email="Shopping Monitor <onboarding@resend.dev>",
    )
    mail = ResendMailService(settings)

    with patch("services.resend_mail.resend") as mock_resend:
        mock_resend.Emails.send = MagicMock()
        mail.send_digest(_sample_email())

    mock_resend.Emails.send.assert_called_once()
    payload = mock_resend.Emails.send.call_args.args[0]
    assert payload["from"] == "Shopping Monitor <onboarding@resend.dev>"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "Your Shopping Monitor digest"


def test_get_mail_service_returns_noop_without_api_key():
    settings = Settings(resend_api_key="")
    assert isinstance(get_mail_service(settings), NoOpMailService)


def test_get_mail_service_returns_resend_with_api_key():
    settings = Settings(resend_api_key="re_test")
    assert isinstance(get_mail_service(settings), ResendMailService)


def test_resend_mail_service_wraps_provider_errors():
    settings = Settings(resend_api_key="re_test")
    mail = ResendMailService(settings)

    with patch("services.resend_mail.resend") as mock_resend:
        mock_resend.Emails.send = MagicMock(side_effect=RuntimeError("rate limited"))
        with pytest.raises(MailServiceError, match="rate limited"):
            mail.send_digest(_sample_email())
