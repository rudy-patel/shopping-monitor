"""Marker expression helpers for integration test setup."""

from __future__ import annotations

from _pytest.mark.expression import Expression


def markexpr_selects_integration(markexpr: str) -> bool:
    """Return True when pytest's -m filter positively selects integration tests."""
    normalized = markexpr.strip()
    if not normalized:
        return False
    return Expression.compile(normalized).evaluate(lambda name: name == "integration")
