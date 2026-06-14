"""Load and validate the benchmark URL catalog."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from scrapers.benchmark.types import CatalogEntry

_CATALOG_PATH = Path(__file__).with_name("catalog.yaml")
_FIXTURE_HOST = "fixtures.local"
_SCENARIO_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def catalog_path() -> Path:
    return _CATALOG_PATH


def load_catalog(*, slugs: list[str] | None = None) -> tuple[str, list[CatalogEntry]]:
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("catalog.yaml must be a mapping")

    version = str(raw.get("catalog_version", "unknown"))
    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list):
        raise ValueError("catalog.yaml entries must be a list")

    entries: list[CatalogEntry] = []
    for item in entries_raw:
        entry = CatalogEntry.model_validate(item)
        _validate_entry_url(entry)
        if slugs is None or entry.slug in slugs:
            entries.append(entry)

    return version, entries


def _validate_entry_url(entry: CatalogEntry) -> None:
    parsed = urlsplit(entry.url)
    host = (parsed.hostname or "").lower()
    if host != _FIXTURE_HOST:
        raise ValueError(
            f"Catalog entry {entry.slug}/{entry.scenario} must use host "
            f"{_FIXTURE_HOST!r}, got {host!r}"
        )
    path = parsed.path.strip("/")
    parts = path.split("/") if path else []
    if len(parts) != 2 or parts[0] != entry.slug or parts[1] != entry.scenario:
        raise ValueError(
            f"Catalog URL path must be /{entry.slug}/{entry.scenario}, "
            f"got {parsed.path!r}"
        )
    if not _SCENARIO_RE.match(entry.scenario):
        raise ValueError(f"Invalid scenario name: {entry.scenario!r}")
