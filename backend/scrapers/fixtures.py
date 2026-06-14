"""Fixture loader for retailer scrape scenarios."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from scrapers.exceptions import FixtureNotFoundError

_SCENARIO_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SCENARIO_MAX_LEN = 48

_BASE_REQUIRED = frozenset({"in_stock", "out_of_stock", "multi_variant"})
_GENERIC_EXTRA = frozenset({"jsonld_friendly", "og_only", "no_extractable_data"})

_VALID_EXTENSIONS = frozenset({"html", "json"})


def _validate_scenario(scenario: str) -> None:
    if len(scenario) > _SCENARIO_MAX_LEN:
        raise ValueError(
            f"scenario name exceeds {_SCENARIO_MAX_LEN} characters: {scenario!r}"
        )
    if not _SCENARIO_RE.match(scenario):
        raise ValueError(
            f"scenario name must match {_SCENARIO_RE.pattern}: {scenario!r}"
        )


def _validate_ext(ext: str) -> None:
    if ext not in _VALID_EXTENSIONS:
        raise ValueError(f"unsupported extension {ext!r}; expected html or json")


def _default_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "test" / "fixtures" / "retailers"  # pragma: allowlist secret
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate retailer fixture root directory")


class FixtureLoader:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else _default_root()

    @property
    def root(self) -> Path:
        return self._root

    def path(self, retailer_slug: str, scenario: str, ext: str = "html") -> Path:
        _validate_scenario(scenario)
        _validate_ext(ext)
        return self._root / retailer_slug / f"{scenario}.{ext}"

    def exists(self, retailer_slug: str, scenario: str, ext: str = "html") -> bool:
        return self.path(retailer_slug, scenario, ext).is_file()

    def load_text(self, retailer_slug: str, scenario: str, ext: str = "html") -> str:
        path = self.path(retailer_slug, scenario, ext)
        if not path.is_file():
            raise FixtureNotFoundError(
                f"Fixture not found: {path}",
                retailer_slug=retailer_slug,
            )
        return path.read_text(encoding="utf-8")

    def load_bytes(self, retailer_slug: str, scenario: str, ext: str = "html") -> bytes:
        path = self.path(retailer_slug, scenario, ext)
        if not path.is_file():
            raise FixtureNotFoundError(
                f"Fixture not found: {path}",
                retailer_slug=retailer_slug,
            )
        return path.read_bytes()

    def load_json(self, retailer_slug: str, scenario: str) -> Any:
        return json.loads(self.load_text(retailer_slug, scenario, ext="json"))

    def record(
        self,
        retailer_slug: str,
        scenario: str,
        content: str | bytes,
        *,
        ext: str = "html",
        overwrite: bool = False,
    ) -> Path:
        _validate_scenario(scenario)
        _validate_ext(ext)
        dest = self.path(retailer_slug, scenario, ext)
        if dest.exists() and not overwrite:
            raise FileExistsError(f"Fixture already exists: {dest}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            if isinstance(content, str):
                tmp.write_text(content, encoding="utf-8")
            else:
                tmp.write_bytes(content)
            os.replace(tmp, dest)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise
        return dest

    def iter_scenarios(self, retailer_slug: str) -> Iterator[tuple[str, str]]:
        retailer_dir = self._root / retailer_slug
        if not retailer_dir.is_dir():
            return iter(())
        for path in sorted(retailer_dir.iterdir()):
            if not path.is_file():
                continue
            stem = path.stem
            ext = path.suffix.lstrip(".")
            if ext in _VALID_EXTENSIONS:
                yield stem, ext

    def required_scenarios(self, retailer_slug: str) -> set[str]:
        required = set(_BASE_REQUIRED)
        if retailer_slug == "generic":
            required |= _GENERIC_EXTRA
        return required
