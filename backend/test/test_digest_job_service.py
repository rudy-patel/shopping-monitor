"""Digest job service unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from core.settings import Settings
from services.digest_job_service import run_send_digests
from services.mail import DigestEmail, MailServiceError, NoOpMailService
from services.profile_service import PROFILE_DEFAULTS
from test.fake_supabase import FakeSupabaseClient

USER_A = "00000000-0000-0000-0000-000000000001"
USER_B = "00000000-0000-0000-0000-000000000002"


def _settings_with_resend() -> Settings:
    return Settings(
        resend_api_key="re_test_key",
        app_base_url="http://localhost:3000",
    )


@pytest.fixture
def fake_client():
    client = FakeSupabaseClient()
    now = datetime.now(UTC)
    for user_id, digest_enabled in ((USER_A, True), (USER_B, True)):
        client.profiles[user_id] = {
            **PROFILE_DEFAULTS,
            "user_id": user_id,
            "email_digest_enabled": digest_enabled,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    client.auth_users[USER_A] = "alice@example.com"
    client.auth_users[USER_B] = "bob@example.com"
    return client


def _insert_notification(
    client: FakeSupabaseClient,
    *,
    user_id: str,
    is_read: bool = False,
    email_sent_at: str | None = None,
) -> str:
    notification_id = str(uuid4())
    product_id = str(uuid4())
    client.products[product_id] = {
        "id": product_id,
        "user_id": user_id,
        "title": "Test Product",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    client.notifications[notification_id] = {
        "id": notification_id,
        "user_id": user_id,
        "product_id": product_id,
        "type": "price_drop",
        "payload": {"old_price_cents": 10000, "new_price_cents": 8000},
        "is_read": is_read,
        "email_sent_at": email_sent_at,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return notification_id


def test_skips_user_with_no_unread(fake_client):
    result = run_send_digests(
        fake_client,
        mail_service=NoOpMailService(),
        settings=_settings_with_resend(),
    )
    assert result.users_skipped_no_unread == 2
    assert result.users_emailed == 0


def test_skips_user_with_digest_disabled(fake_client):
    fake_client.profiles[USER_A]["email_digest_enabled"] = False
    _insert_notification(fake_client, user_id=USER_A)

    result = run_send_digests(
        fake_client,
        mail_service=NoOpMailService(),
        settings=_settings_with_resend(),
    )

    assert result.users_skipped_digest_disabled == 1
    assert result.users_emailed == 0


def test_skips_user_without_auth_email(fake_client):
    fake_client.auth_users.pop(USER_A)
    notification_id = _insert_notification(fake_client, user_id=USER_A)

    result = run_send_digests(
        fake_client,
        mail_service=NoOpMailService(),
        settings=_settings_with_resend(),
    )

    assert result.users_skipped_no_email == 1
    assert fake_client.notifications[notification_id]["email_sent_at"] is None


def test_marks_email_sent_on_success(fake_client):
    notification_id = _insert_notification(fake_client, user_id=USER_A)
    mail = NoOpMailService()

    result = run_send_digests(
        fake_client,
        mail_service=mail,
        settings=_settings_with_resend(),
    )

    assert result.users_emailed == 1
    assert result.notifications_marked_sent == 1
    assert fake_client.notifications[notification_id]["email_sent_at"] is not None
    assert len(mail.sent) == 1
    assert mail.sent[0].to_email == "alice@example.com"


def test_does_not_mark_on_send_failure(fake_client):
    notification_id = _insert_notification(fake_client, user_id=USER_A)

    class FailingMail:
        def send_digest(self, email: DigestEmail) -> None:
            raise MailServiceError("provider down")

    result = run_send_digests(
        fake_client,
        mail_service=FailingMail(),
        settings=_settings_with_resend(),
    )

    assert result.users_failed == 1
    assert result.notifications_marked_sent == 0
    assert fake_client.notifications[notification_id]["email_sent_at"] is None


def test_noop_provider_does_not_send_or_mark(fake_client):
    notification_id = _insert_notification(fake_client, user_id=USER_A)
    mail = NoOpMailService()

    result = run_send_digests(
        fake_client,
        mail_service=mail,
        settings=Settings(resend_api_key="", app_base_url="http://localhost:3000"),
    )

    assert result.mail_provider == "noop"
    assert result.users_emailed == 0
    assert len(mail.sent) == 0
    assert fake_client.notifications[notification_id]["email_sent_at"] is None


def test_skips_already_emailed_notifications(fake_client):
    sent_at = datetime.now(UTC).isoformat()
    _insert_notification(fake_client, user_id=USER_A, email_sent_at=sent_at)

    result = run_send_digests(
        fake_client,
        mail_service=NoOpMailService(),
        settings=_settings_with_resend(),
    )

    assert result.users_skipped_no_unread == 2
    assert result.users_emailed == 0


def test_skips_read_notifications(fake_client):
    _insert_notification(fake_client, user_id=USER_A, is_read=True)

    result = run_send_digests(
        fake_client,
        mail_service=NoOpMailService(),
        settings=_settings_with_resend(),
    )

    assert result.users_skipped_no_unread >= 1
    assert result.users_emailed == 0


def test_excludes_notifications_outside_retention_window(fake_client):
    notification_id = str(uuid4())
    product_id = str(uuid4())
    old_created = (datetime.now(UTC) - timedelta(days=91)).isoformat()
    fake_client.products[product_id] = {
        "id": product_id,
        "user_id": USER_A,
        "title": "Old Product",
        "status": "active",
        "created_at": old_created,
        "updated_at": old_created,
    }
    fake_client.notifications[notification_id] = {
        "id": notification_id,
        "user_id": USER_A,
        "product_id": product_id,
        "type": "price_drop",
        "payload": {},
        "is_read": False,
        "email_sent_at": None,
        "created_at": old_created,
    }

    result = run_send_digests(
        fake_client,
        mail_service=NoOpMailService(),
        settings=_settings_with_resend(),
    )

    assert result.users_skipped_no_unread >= 1
    assert result.users_emailed == 0
