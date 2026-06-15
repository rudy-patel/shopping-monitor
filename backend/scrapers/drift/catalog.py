"""Load and validate the drift URL catalog."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml

from scrapers.benchmark.catalog import load_catalog as load_benchmark_catalog
from scrapers.drift.types import DriftCatalogEntry

_CATALOG_PATH = Path(__file__).with_name("catalog.yaml")
_EXCLUDED_SLUGS = frozenset({"generic"})


def catalog_path() -> Path:
    return _CATALOG_PATH


def snapshots_dir() -> Path:
    return Path(__file__).with_name("snapshots")


def snapshot_path(slug: str) -> Path:
    return snapshots_dir() / f"{slug}.json"


def load_catalog(*, slugs: list[str] | None = None) -> tuple[str, list[DriftCatalogEntry]]:
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("drift catalog.yaml must be a mapping")

    version = str(raw.get("catalog_version", "unknown"))
    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list):
        raise ValueError("drift catalog.yaml entries must be a list")

    _, benchmark_entries = load_benchmark_catalog()
    benchmark_expect = {
        (entry.slug, entry.scenario): entry.expect for entry in benchmark_entries
    }

    entries: list[DriftCatalogEntry] = []
    for item in entries_raw:
        entry = DriftCatalogEntry.model_validate(item)
        _validate_live_url(entry)
        if entry.slug in _EXCLUDED_SLUGS:
            raise ValueError(f"drift catalog must not include excluded slug {entry.slug!r}")
        expect_key = (entry.slug, entry.scenario)
        if expect_key not in benchmark_expect:
            raise ValueError(
                f"Drift entry {entry.slug}/{entry.scenario} missing from benchmark catalog"
            )
        entry = entry.model_copy(update={"expect": benchmark_expect[expect_key]})
        if slugs is None or entry.slug in slugs:
            entries.append(entry)

    return version, entries


def _validate_live_url(entry: DriftCatalogEntry) -> None:
    parsed = urlsplit(entry.url)
    host = (parsed.hostname or "").lower()
    if not host or host in {"fixtures.local", "localhost"}:
        raise ValueError(
            f"Drift catalog entry {entry.slug!r} must use a live retailer URL, "
            f"got host {host!r}"
        )
    if not parsed.scheme.startswith("http"):
        raise ValueError(f"Drift catalog entry {entry.slug!r} must use http(s) URL")
