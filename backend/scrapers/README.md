# Retailer scrapers

This package defines the scraper contract, retailer registry, fixture harness, and the single canonical HTTP entry point for V1 retailer modules.

## Contract

`scrape(url) -> ProductSnapshot` is the function signature every registered retailer must implement. `ProductSnapshot` (in `contract.py`) is the normalized result written to `product_listings` — price in CAD cents, variant metadata, breadcrumbs, scrape source, and a bounded `raw_snapshot` dict (no full HTML dumps).

## Adding a retailer scraper

1. Choose a **slug** — snake_case, e.g. `bestbuy_ca`.
2. Create a module under `backend/scrapers/` (or a subpackage) implementing `scrape(url: str) -> ProductSnapshot`.
3. Register at import time:

```python
from scrapers.contract import ProductSnapshot, ScrapeSource
from scrapers.registry import RetailerEntry, register

def scrape(url: str) -> ProductSnapshot:
    ...

register(
    RetailerEntry(
        slug="bestbuy_ca",
        domains=("bestbuy.ca", "www.bestbuy.ca"),
        default_category="tech",
        scrape=scrape,
        default_strategy=ScrapeSource.HTTP_PARSE,
    )
)
```

4. Add retailer fixture files under `backend/test/` per the path convention below.

## Fixture convention

Path: `backend/test/fixtures/retailers/<retailer_slug>/<scenario>.<ext>`  <!-- pragma: allowlist secret -->

- `<retailer_slug>` matches `RetailerEntry.slug` (or `fixture_dir` if set).
- `<scenario>` — snake_case ASCII, max 48 chars, `^[a-z][a-z0-9_]*$`.
- `<ext>` — `html` for page captures, `json` for API/JSON-LD captures. A scenario may have both (e.g. `in_stock.html` + `in_stock.json`).

**Required scenarios** for every retailer: `in_stock`, `out_of_stock`, `multi_variant`.

**Additional required scenarios** for the `generic` slug: `jsonld_friendly`, `og_only`, `no_extractable_data`.

Load fixture files in tests or scraper code via `FixtureLoader`:

```python
# pragma: allowlist secret
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

loader = FixtureLoader()
html = loader.load_text("bestbuy_ca", "in_stock")
```

## HTTP requests — use `scraper_fetch` only

Retailer scrapers **must** call `scrapers.http.scraper_fetch()` for outbound requests. Do **not** import `httpx`, `curl_cffi`, or `requests` directly in scraper modules — `test_scraper_http_guard.py` enforces this.

- **Fixture mode** (default): `scraper_fetch` raises the fixture-mode network guard — no socket is opened.
- **Live or record mode**: delegates to `httpx`.

The scraper mode env var is read by `scrapers.mode.get_scraper_mode()` today. This will move under the central settings loader in T1.2.

## Recording fixture files

`FixtureLoader.record(...)` is the canonical writer for manual fixture capture (T2.8) and the future drift-detection workflow (T5.5). Nothing auto-records in record mode; callers invoke `record` explicitly after a live fetch.

```python
# pragma: allowlist secret
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret
from scrapers.http import scraper_fetch

response = scraper_fetch(url, retailer_slug="bestbuy_ca")  # live/record only
FixtureLoader().record("bestbuy_ca", "in_stock", response.body_text, overwrite=True)
```

## Example `scrape(url)` return value

```python
from datetime import datetime, timezone

from scrapers.contract import ProductSnapshot, ScrapeSource

ProductSnapshot(
    retailer_slug="bestbuy_ca",
    url="https://www.bestbuy.ca/en-ca/product/12345",
    title="Wireless Headphones",
    brand="Sony",
    current_price_cents=14999,
    currency_seen="CAD",
    is_in_stock=True,
    scraped_at=datetime.now(timezone.utc),
    source=ScrapeSource.FIXTURE,
    raw_snapshot={"sku": "12345"},
)
```

Callers of `scrape(url)` (the product API in T2.5) reject non-CAD listings per PRD §7.2; the snapshot itself reports `currency_seen` honestly.
