"""Compare live fingerprints to committed drift baselines."""

from __future__ import annotations

import json
from typing import Any

from scrapers.benchmark.types import FieldExpect
from scrapers.contract import ProductSnapshot
from scrapers.drift.catalog import snapshot_path
from scrapers.drift.normalize import check_expect_fields, normalize
from scrapers.drift.types import DriftSnapshot


def load_baseline(slug: str) -> DriftSnapshot:
    path = snapshot_path(slug)
    if not path.is_file():
        raise FileNotFoundError(f"Missing drift baseline snapshot: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DriftSnapshot.model_validate(payload)


def write_baseline(slug: str, snapshot: DriftSnapshot) -> None:
    path = snapshot_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fingerprint_diff(
    baseline: DriftSnapshot,
    live: DriftSnapshot,
) -> dict[str, dict[str, Any]]:
    diff: dict[str, dict[str, Any]] = {}
    for field_name in DriftSnapshot.model_fields:
        baseline_value = getattr(baseline, field_name)
        live_value = getattr(live, field_name)
        if baseline_value != live_value:
            diff[field_name] = {"baseline": baseline_value, "live": live_value}
    return diff


def compare_to_baseline(
    *,
    slug: str,
    live_snapshot: ProductSnapshot,
    expect: FieldExpect,
) -> tuple[bool, dict[str, dict[str, Any]], DriftSnapshot, DriftSnapshot, list[str]]:
    baseline = load_baseline(slug)
    live_fingerprint = normalize(live_snapshot)
    expect_failures = check_expect_fields(live_snapshot, expect)
    diff = fingerprint_diff(baseline, live_fingerprint)
    ok = not diff and not expect_failures
    return ok, diff, baseline, live_fingerprint, expect_failures
