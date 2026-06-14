"""Re-export protected-account helpers for integration tests and smoke scripts."""

from __future__ import annotations

from core.protected_accounts import (  # noqa: F401
    DISPOSABLE_EMAIL_DOMAIN,
    DISPOSABLE_EMAIL_PREFIX,
    PROTECTED_EMAILS,
    PROTECTED_USER_IDS,
    assert_safe_to_delete,
    disposable_email,
)
