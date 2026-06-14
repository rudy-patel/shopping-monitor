"""Manual live Gemini categorization smoke. NOT run in CI."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from core.settings import get_settings  # noqa: E402
from services.categorizer import CategorizationContext, DefaultCategorizer  # noqa: E402
from services.factory import build_retailer_default_categories, get_categorizer  # noqa: E402
from services.llm import NoOpLlmProvider  # noqa: E402


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
        "--expect-heuristic",
        action="store_true",
        help="Assert categorization did not use the LLM path (no API key check).",
    )
    args = parser.parse_args()

    if args.live:
        if not get_settings().gemini_api_key.strip():
            print("GEMINI_API_KEY is required for --live smoke.", file=sys.stderr)
            return 1
        categorizer = get_categorizer()
        mode = "live"
    else:
        categorizer = DefaultCategorizer(
            NoOpLlmProvider(),
            retailer_defaults=build_retailer_default_categories(),
        )
        mode = "dry_run"

    ctx = CategorizationContext(
        title="Sony WH-1000XM5",
        brand="Sony",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Headphones"],
    )

    started = time.perf_counter()
    result = categorizer.categorize(ctx)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    print(f"mode={mode}")
    print(f"category={result.category}")
    print(f"source={result.source}")
    print(f"elapsed_ms={elapsed_ms}")

    if args.expect_heuristic and result.source == "llm":
        print("Expected heuristic fallback but source was llm", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
