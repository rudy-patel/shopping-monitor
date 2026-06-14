"""Scraper benchmark harness (PRD §7.9, ROADMAP T5.1)."""

from scrapers.benchmark.runner import run_benchmark
from scrapers.benchmark.types import BenchmarkReport

__all__ = ["BenchmarkReport", "run_benchmark"]
