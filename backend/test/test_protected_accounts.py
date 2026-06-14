"""Protected-account guard unit tests."""

from __future__ import annotations

import pytest

from core.protected_accounts import (
    PROTECTED_EMAILS,
    PROTECTED_USER_IDS,
    assert_safe_to_delete,
    disposable_email,
)

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def test_disposable_email_uses_expected_domain():
    email = disposable_email()
    assert email.startswith("delete-account-")
    assert email.endswith("@shopping-monitor-test.invalid")


@pytest.mark.parametrize("user_id", sorted(PROTECTED_USER_IDS))
def test_assert_safe_to_delete_rejects_protected_user_ids(user_id: str):
    with pytest.raises(RuntimeError, match="protected user_id"):
        assert_safe_to_delete(user_id=user_id, email=None)


@pytest.mark.parametrize("email", sorted(PROTECTED_EMAILS))
def test_assert_safe_to_delete_rejects_protected_emails(email: str):
    with pytest.raises(RuntimeError, match="protected email"):
        assert_safe_to_delete(user_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", email=email)


def test_assert_safe_to_delete_allows_disposable_identity():
    assert_safe_to_delete(
        user_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        email=disposable_email(),
    )
