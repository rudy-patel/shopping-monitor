"""Smoke test for the public services package surface."""

from __future__ import annotations

import importlib

import services


def test_services_public_api_importable():
    for name in services.__all__:
        assert hasattr(services, name), f"missing export: {name}"


def test_services_package_reimportable():
    reloaded = importlib.reload(services)
    assert reloaded.CANONICAL_CURRENCY == "CAD"
