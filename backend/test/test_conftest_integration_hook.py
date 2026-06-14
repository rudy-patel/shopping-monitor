"""Regression tests for integration env setup gating in conftest."""

from __future__ import annotations

from integration_markexpr import markexpr_selects_integration


def test_markexpr_selects_integration_positive_cases() -> None:
    assert markexpr_selects_integration("integration") is True
    assert markexpr_selects_integration("integration or slow") is True


def test_markexpr_selects_integration_negative_cases() -> None:
    assert markexpr_selects_integration("") is False
    assert markexpr_selects_integration("not integration") is False
    assert markexpr_selects_integration("not integration and slow") is False
