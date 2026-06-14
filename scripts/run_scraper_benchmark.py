#!/usr/bin/env python3
"""Run the scraper benchmark harness (PRD §7.9, ROADMAP T5.1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from scrapers.benchmark.runner import run_benchmark  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scraper strategy benchmarks.")
    parser.add_argument(
        "--out",
        type=Path,
        help="Write JSON report to this path (stdout always prints full JSON).",
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Filter catalog to one or more retailer slugs (repeatable).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live network fetches (requires SCRAPER_MODE=live or record).",
    )
    parser.add_argument(
        "--with-playwright",
        action="store_true",
        help="Attempt Playwright strategy when installed (live mode only).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=None,
        help="Retry count per strategy (default: 0 in fixture mode, 1 when --live).",
    )
    args = parser.parse_args()

    report = run_benchmark(
        slugs=args.slugs,
        live=args.live,
        with_playwright=args.with_playwright,
        retries=args.retries,
    )

    payload = report.model_dump(mode="json")
    text = json.dumps(payload, indent=2)
    print(text)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote report to {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
