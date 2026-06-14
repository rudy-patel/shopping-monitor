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

Path: `backend/test/<fixture-dir>/retailers/<retailer_slug>/<scenario>.<ext>` where `<fixture-dir>` is the standard test fixture folder name.

- `<retailer_slug>` matches `RetailerEntry.slug` (or `fixture_dir` if set).
- `<scenario>` — snake_case ASCII, max 48 chars, `^[a-z][a-z0-9_]*$`.
- `<ext>` — `html` for page captures, `json` for API/JSON-LD captures. A scenario may have both (e.g. `in_stock.html` + `in_stock.json`).

**Required scenarios** for every retailer: `in_stock`, `out_of_stock`, `multi_variant`.

**Additional required scenarios** for the `generic` slug: `jsonld_friendly`, `og_only`, `no_extractable_data`.

Load fixture files in tests or scraper code via `FixtureLoader`:

```python
from scrapers.fixtures import FixtureLoader  # pragma: allowlist secret

loader = FixtureLoader()
html = loader.load_text("bestbuy_ca", "in_stock")
```

### Fixture URL convention (fixture mode)

In `SCRAPER_MODE=fixtures`, retailer scrapers resolve scenario names from synthetic URLs:

```
https://fixtures.local/<retailer_slug>/<scenario>
```

Use `resolve_fixture_scenario(url, retailer_slug)` from `scrapers.fixture_url` to parse the scenario segment. Examples:

- `https://fixtures.local/generic/jsonld_friendly`
- `https://fixtures.local/bestbuy_ca/in_stock` (T2.3)

Rules: host must be `fixtures.local`; path must be `/<retailer_slug>/<scenario>` where scenario matches `^[a-z][a-z0-9_]*$`. Unknown or missing scenarios raise `FixtureNotFoundError`.

`lookup_by_url()` also resolves `fixtures.local/<retailer_slug>/...` URLs to the matching registry entry (used by the Product API in fixture mode).

Production retailer modules are registered via `scrapers.bootstrap` (import for side effects in `main.py`). That module registers `generic` (unknown-domain fallback), `bestbuy_ca`, `palmisleskate`, and `tikiroomskate` (shared Shopify JSON-LD + theme meta parser; T5.2).

## Shopify retailers (T5.2)

Shared factory in `scrapers/shopify.py` with variant extraction in `scrapers/extraction/shopify.py` (JSON-LD/OG plus Shopify `var meta` merge). Record live fixtures:

```bash
cd backend && source venv/bin/activate
SCRAPER_MODE=record python ../scripts/record_shopify_fixtures.py \
  --slug palmisleskate --scenario in_stock \
  --url "https://palmisleskateshop.com/products/..."
```

## HTTP requests — use `scraper_fetch` only

Retailer scrapers **must** call `scrapers.http.scraper_fetch()` for outbound requests. Do **not** import `httpx`, `curl_cffi`, or `requests` directly in scraper modules — `test_scraper_http_guard.py` enforces this.

- **Fixture mode** (default): `scraper_fetch` raises the fixture-mode network guard — no socket is opened.
- **Live or record mode**: uses `curl_cffi` browser impersonation first, with `httpx` fallback. The `bestbuy_ca` scraper adds a measured JSON product API fallback when the HTML PDP is blocked (Akamai 403); see `scrapers/extraction/bestbuy_api.py`.

`get_scraper_mode()` reads `core.settings.get_settings().scraper_mode` (backed by the `SCRAPER_MODE` env var).

## Recording fixture files

`FixtureLoader.record(...)` is the canonical writer for manual fixture capture (T2.8) and the future drift-detection workflow (T5.5). Nothing auto-records in record mode; callers invoke `record` explicitly after a live fetch.

```bash
cd backend && source venv/bin/activate
SCRAPER_MODE=record python ../scripts/record_bestbuy_fixtures.py \
  --scenario in_stock --url "https://www.bestbuy.ca/en-ca/product/..."
```

When the HTML PDP is blocked (Akamai 403), the record script falls back to Best Buy's JSON product API and writes a JSON-LD HTML fixture plus a raw `.json` snapshot.

```python
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

## Benchmark harness (T5.1)

Compare extraction strategies per retailer before committing registry defaults. Catalog lives in `scrapers/benchmark/catalog.yaml` (fixture URLs only in T5.1).

```bash
# Fixture-mode report (CI-safe)
make benchmark-retailers

# Filter one retailer
cd backend && source venv/bin/activate
SCRAPER_MODE=fixtures python ../scripts/run_scraper_benchmark.py --slug bestbuy_ca

# Live run (human-triggered; not in CI)
SCRAPER_MODE=live python ../scripts/run_scraper_benchmark.py --live \
  --out ../docs/benchmarks/live-$(date +%Y-%m-%d).json
```

**Strategies measured:** `structured_data` (JSON-LD/OG + retailer parsers), `http_parse` (`scraper_fetch` + parser, with retailer API sub-probes such as Best Buy JSON API), and optional `playwright` (`--with-playwright`, requires `requirements-benchmark.txt`).

Reports are committed under `docs/benchmarks/`. Recommendations are advisory until a human confirms before T5.2+ scraper PRs copy `registry_snippet` values.
