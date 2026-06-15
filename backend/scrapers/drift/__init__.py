"""Retailer drift detection — compare live scrapes to fixture baselines."""

from scrapers.drift.runner import run_drift_checks, scrape_fixture_baseline
from scrapers.drift.types import DriftCheckResult, DriftReport, DriftSnapshot

__all__ = [
    "DriftCheckResult",
    "DriftReport",
    "DriftSnapshot",
    "run_drift_checks",
    "scrape_fixture_baseline",
]
