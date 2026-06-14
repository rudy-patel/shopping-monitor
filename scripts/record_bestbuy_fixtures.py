#!/usr/bin/env python3
"""Record Best Buy Canada HTML fixtures from live product URLs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from scrapers.bestbuy_ca import extract_bestbuy_html  # noqa: E402
from scrapers.fixtures import FixtureLoader  # noqa: E402  # pragma: allowlist secret
from scrapers.http import scraper_fetch  # noqa: E402
from scrapers.mode import require_not_fixtures_mode  # noqa: E402

_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "Attention Required",
)


def _validate_response(body_text: str, status_code: int) -> None:
    if status_code != 200:
        raise SystemExit(f"Expected HTTP 200, got {status_code}")
    if len(body_text.strip()) < 1000:
        raise SystemExit("Response body is too small to be a product page")
    lowered = body_text.lower()
    if any(marker.lower() in lowered for marker in _CHALLENGE_MARKERS):
        raise SystemExit("Response looks like a Cloudflare challenge page")


def _print_summary(extracted) -> None:
    print("Field summary:")
    print(f"  title: {extracted.title!r}")
    print(f"  price_cents: {extracted.price_cents}")
    print(f"  currency: {extracted.currency!r}")
    print(f"  is_in_stock: {extracted.is_in_stock}")
    print(f"  variant_count: {len(extracted.available_variants)}")
    if extracted.available_variants:
        skus = [variant.sku for variant in extracted.available_variants if variant.sku]
        print(f"  variant_skus: {skus}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="Fixture scenario name")
    parser.add_argument("--url", required=True, help="Live Best Buy Canada product URL")
    args = parser.parse_args()

    require_not_fixtures_mode()
    response = scraper_fetch(args.url, retailer_slug="bestbuy_ca")
    _validate_response(response.body_text, response.status_code)

    extracted = extract_bestbuy_html(response.body_text, url=args.url)
    if extracted.title is None:
        print("Warning: title not extracted from recorded HTML", file=sys.stderr)
    if extracted.price_cents is None:
        print("Warning: price not extracted from recorded HTML", file=sys.stderr)

    dest = FixtureLoader().record(
        "bestbuy_ca",
        args.scenario,
        response.body_text,
        overwrite=True,
    )
    print(f"Recorded fixture: {dest}")
    _print_summary(extracted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
