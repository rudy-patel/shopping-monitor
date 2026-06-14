# Scraper benchmark reports (PRD §15.3)

Historical snapshots of per-retailer strategy comparisons. Used to justify `default_strategy` and `fallback_strategies` in retailer registry entries (T5.2+).

## Naming

- `fixtures-YYYY-MM-DD.json` — fixture-mode run (CI-safe, default for catalog validation)
- `live-YYYY-MM-DD.json` — live network run (human/agent triggered during retailer expansion)

## Regenerate fixture report

```bash
make benchmark-retailers
```

Or directly:

```bash
cd backend && source venv/bin/activate
SCRAPER_MODE=fixtures python ../scripts/run_scraper_benchmark.py \
  --out ../docs/benchmarks/fixtures-$(date +%Y-%m-%d).json
```

## Live + optional Playwright

```bash
pip install -r requirements-benchmark.txt
playwright install chromium
SCRAPER_MODE=live python ../scripts/run_scraper_benchmark.py --live \
  --with-playwright --out ../docs/benchmarks/live-$(date +%Y-%m-%d).json
```

Review `summaries[].registry_snippet` before copying values into retailer modules.
