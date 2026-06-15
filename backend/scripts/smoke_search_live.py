"""Manual live Gemini search smoke (T8.11). NOT run in CI.

Usage:
  python backend/scripts/smoke_search_live.py                   # dry run, no API call
  python backend/scripts/smoke_search_live.py --live --query "AirPods Pro"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from core.settings import get_settings  # noqa: E402
from services.factory import get_llm_provider  # noqa: E402
from services.llm import NoOpLlmProvider  # noqa: E402
from services.search_service import _classify_candidate, _dedupe_and_rank  # noqa: E402


def main() -> int:
    if sys.version_info < (3, 12):
        print(
            "Python 3.12+ is required for the backend. "
            f"Current interpreter: {sys.version.split()[0]}",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the real Gemini API (requires GEMINI_API_KEY). Never use in CI.",
    )
    parser.add_argument(
        "--query",
        default="AirPods Pro",
        help="Search query to send to Gemini.",
    )
    args = parser.parse_args()

    # Register retailers so the classifier knows about supported slugs.
    import scrapers.bootstrap  # noqa: F401

    if args.live:
        if not get_settings().gemini_api_key.strip():
            print("GEMINI_API_KEY is required for --live smoke.", file=sys.stderr)
            return 1
        llm = get_llm_provider()
        mode = "live"
    else:
        llm = NoOpLlmProvider()
        mode = "dry_run"

    started = time.perf_counter()
    try:
        result = llm.search(query=args.query)
    except Exception as exc:
        print(f"mode={mode}")
        print(f"error={exc.__class__.__name__}: {exc}")
        return 1
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    print(f"mode={mode}")
    print(f"query={args.query}")
    print(f"raw_candidate_count={len(result.candidates)}")
    print(f"elapsed_ms={elapsed_ms}")

    classified = [item for c in result.candidates if (item := _classify_candidate(c))]
    ranked = _dedupe_and_rank(classified)
    print(f"ranked_count={len(ranked)}")
    for index, item in enumerate(ranked, start=1):
        print(
            f"result_{index} supported={item.supported} retailer={item.retailer_slug} "
            f"title={item.title!r}"
        )

    if args.live:
        print(
            json.dumps(
                {"ranked_results": [item.to_dict() for item in ranked]},
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
