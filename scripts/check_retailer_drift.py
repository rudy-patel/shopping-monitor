#!/usr/bin/env python3
"""Compare live retailer scrapes to committed drift baselines (T5.5)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import scrapers.bootstrap  # noqa: E402, F401
from scrapers.drift.runner import run_drift_checks  # noqa: E402
from scrapers.mode import get_scraper_mode, require_not_fixtures_mode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run live drift checks against canonical retailer URLs. "
            "Requires SCRAPER_MODE=live (never runs in fixtures/CI)."
        )
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Check one or more retailer slugs (repeatable). Default: full catalog.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="When filing issues, log actions without GitHub writes.",
    )
    parser.add_argument(
        "--file-issues",
        action="store_true",
        help="Open/update/close GitHub issues (requires GITHUB_TOKEN + GITHUB_REPOSITORY).",
    )
    parser.add_argument(
        "--no-issues",
        action="store_true",
        help="Skip GitHub issue sync (default for local make target).",
    )
    parser.add_argument(
        "--run-url",
        default=None,
        help="Optional link included in GitHub issue bodies.",
    )
    args = parser.parse_args()

    if args.file_issues and args.no_issues:
        print("Choose either --file-issues or --no-issues", file=sys.stderr)
        return 2

    require_not_fixtures_mode()
    if get_scraper_mode().value != "live":
        print(
            "SCRAPER_MODE must be live for drift checks. "
            "Use SCRAPER_MODE=fixtures make update-drift-snapshots to refresh baselines.",
            file=sys.stderr,
        )
        return 2

    file_issues = args.file_issues and not args.no_issues
    token = os.environ.get("GITHUB_TOKEN") if file_issues else None
    if file_issues and not token:
        print("GITHUB_TOKEN is required when --file-issues is set", file=sys.stderr)
        return 2

    report = run_drift_checks(
        slugs=args.slugs,
        file_issues=file_issues,
        dry_run=args.dry_run,
        run_url=args.run_url,
        github_token=token,
    )

    payload = report.model_dump(mode="json")
    print(json.dumps(payload, indent=2, sort_keys=True))

    for result in report.results:
        if result.status != "ok":
            print(
                f"DRIFT {result.slug}: {result.status} — {result.message or 'see report'}",
                file=sys.stderr,
            )

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
