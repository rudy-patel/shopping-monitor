"""Regression: pytest autouse fixture must block live Resend even when env has a key."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from core.settings import clear_settings_cache, get_settings
from services.factory import get_mail_service
from services.mail import DigestEmail, DigestNotificationEntry, NoOpMailService
from services.notifications import NotificationKind
from services.resend_mail import ResendMailService


def test_settings_resend_key_cleared_during_pytest():
    settings = get_settings()
    assert settings.resend_api_key == ""
    assert isinstance(get_mail_service(settings), NoOpMailService)


def test_resend_sdk_is_mocked_by_autouse_fixture():
    import services.resend_mail as resend_mail_module

    assert isinstance(resend_mail_module.resend.Emails.send, MagicMock)

    settings = __import__("core.settings", fromlist=["Settings"]).Settings(
        resend_api_key="re_test"
    )
    clear_settings_cache()
    service = ResendMailService(settings)
    service.send_digest(
        DigestEmail(
            to_email="user@example.com",
            subject="Digest",
            text_body="t",
            html_body="h",
            entries=[
                DigestNotificationEntry(
                    notification_id=uuid4(),
                    type=NotificationKind.PRICE_DROP,
                    product_id=uuid4(),
                    product_title="P",
                    summary="s",
                    deep_link="http://localhost:3000/products/x",
                    created_at=datetime.now(UTC),
                )
            ],
        )
    )
    resend_mail_module.resend.Emails.send.assert_called_once()
