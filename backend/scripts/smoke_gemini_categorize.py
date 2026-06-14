"""Manual live Gemini categorization smoke. NOT run in CI."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from services.categorizer import CategorizationContext  # noqa: E402
from services.factory import get_categorizer  # noqa: E402


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
        "--expect-heuristic",
        action="store_true",
        help="Assert categorization did not use the LLM path (no API key check).",
    )
    args = parser.parse_args()

    categorizer = get_categorizer()
    ctx = CategorizationContext(
        title="Sony WH-1000XM5",
        brand="Sony",
        retailer_slug="bestbuy_ca",
        breadcrumbs=["Electronics", "Headphones"],
    )

    started = time.perf_counter()
    result = categorizer.categorize(ctx)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    print(f"category={result.category}")
    print(f"source={result.source}")
    print(f"elapsed_ms={elapsed_ms}")

    if args.expect_heuristic and result.source == "llm":
        print("Expected heuristic fallback but source was llm", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
