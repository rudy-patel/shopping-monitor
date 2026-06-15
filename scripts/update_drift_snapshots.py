#!/usr/bin/env python3
"""Regenerate committed drift baseline snapshots from fixture-mode scrapes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import scrapers.bootstrap  # noqa: E402, F401
from scrapers.drift.catalog import load_catalog  # noqa: E402
from scrapers.drift.compare import write_baseline  # noqa: E402
from scrapers.drift.normalize import normalize  # noqa: E402
from scrapers.drift.runner import scrape_fixture_baseline  # noqa: E402
from scrapers.mode import get_scraper_mode, require_fixtures_mode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Update one or more retailer slugs (repeatable). Default: all catalog entries.",
    )
    args = parser.parse_args()

    require_fixtures_mode()
    if get_scraper_mode().value != "fixtures":
        print("SCRAPER_MODE must be fixtures", file=sys.stderr)
        return 2

    _, entries = load_catalog(slugs=args.slugs)
    if not entries:
        print("No catalog entries matched", file=sys.stderr)
        return 1

    for entry in entries:
        snapshot = scrape_fixture_baseline(entry.slug, entry.scenario)
        fingerprint = normalize(snapshot)
        write_baseline(entry.slug, fingerprint)
        print(f"Wrote drift baseline: {entry.slug} ({entry.scenario})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
