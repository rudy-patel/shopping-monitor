#!/usr/bin/env python3
"""Validate migration naming and documentation coverage."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "backend" / "db" / "migrations"
DOC_FILES = [
    ROOT / "docs" / "DATABASE.md",
]
NAME_PATTERN = re.compile(r"^(?P<seq>\d{3})_[a-z0-9_]+\.sql$")


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        print(f"ERROR: Missing migrations directory: {MIGRATIONS_DIR}")
        return 1

    migration_files = sorted(
        p.name for p in MIGRATIONS_DIR.glob("*.sql")
    )

    if not migration_files:
        print(
            "Migration validation passed (no .sql migrations yet; "
            "add files as 001_description.sql when schema work begins)."
        )
        return 0

    errors: list[str] = []
    sequence_numbers: dict[str, str] = {}

    for filename in migration_files:
        match = NAME_PATTERN.match(filename)
        if not match:
            errors.append(
                f"Invalid migration filename '{filename}'. "
                "Expected format: 001_description.sql"
            )
            continue

        seq = match.group("seq")
        if seq in sequence_numbers:
            errors.append(
                f"Duplicate migration sequence '{seq}': "
                f"{sequence_numbers[seq]} and {filename}"
            )
        else:
            sequence_numbers[seq] = filename

    docs_text = "\n".join(
        doc.read_text(encoding="utf-8") for doc in DOC_FILES if doc.exists()
    )

    for filename in migration_files:
        if filename not in docs_text:
            errors.append(
                f"Migration '{filename}' is not referenced in docs/DATABASE.md"
            )

    if errors:
        print("Migration validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print(
        f"Migration validation passed ({len(migration_files)} files, "
        "docs references verified)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
