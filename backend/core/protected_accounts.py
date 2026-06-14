"""Hard-deny list for account deletion (dev user, owner accounts)."""

from __future__ import annotations

from uuid import uuid4

PROTECTED_USER_IDS = frozenset({"00000000-0000-0000-0000-000000000001"})
PROTECTED_EMAILS = frozenset({"rutvik@ualberta.ca"})
DISPOSABLE_EMAIL_DOMAIN = "shopping-monitor-test.invalid"
DISPOSABLE_EMAIL_PREFIX = "delete-account-"


def disposable_email() -> str:
    return f"{DISPOSABLE_EMAIL_PREFIX}{uuid4()}@{DISPOSABLE_EMAIL_DOMAIN}"


def assert_safe_to_delete(*, user_id: str, email: str | None) -> None:
    if user_id in PROTECTED_USER_IDS:
        raise RuntimeError(f"Refusing to delete protected user_id={user_id}")
    if email and email.strip().lower() in {e.lower() for e in PROTECTED_EMAILS}:
        raise RuntimeError(f"Refusing to delete protected email={email}")
