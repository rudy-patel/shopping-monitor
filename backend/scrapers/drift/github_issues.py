"""GitHub issue helpers for local drift runs (optional --file-issues)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from scrapers.drift.types import DriftCheckResult, IssueStatusKind

_ISSUE_TITLE_RE = re.compile(
    r"^\[retailer-drift\]\s+(?P<slug>[a-z][a-z0-9_]*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


def resolve_github_repo() -> GitHubRepo:
    env_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if env_repo and "/" in env_repo:
        owner, name = env_repo.split("/", 1)
        return GitHubRepo(owner=owner, name=name)
    raise RuntimeError(
        "Set GITHUB_REPOSITORY=owner/repo to file drift issues, "
        "or pass --no-issues / use --dry-run."
    )


def issue_title(slug: str, kind: IssueStatusKind) -> str:
    label = kind.replace("_", " ")
    return f"[retailer-drift] {slug} — {label}"


def format_issue_body(result: DriftCheckResult, *, run_url: str | None = None) -> str:
    lines = [
        f"Retailer drift check failed for `{result.slug}`.",
        "",
        f"- **Status:** `{result.status}`",
        f"- **URL:** {result.url}",
        f"- **Scenario:** `{result.scenario}`",
    ]
    if result.message:
        lines.extend(["", f"**Message:** {result.message}"])
    if result.blocked_markers:
        lines.extend(["", "**Blocked markers:**", *[f"- `{marker}`" for marker in result.blocked_markers]])
    if result.expect_failures:
        lines.extend(["", "**Missing expected fields:**", *[f"- `{field}`" for field in result.expect_failures]])
    if result.diff:
        lines.extend(["", "**Fingerprint diff:**", "```json", _pretty_json(result.diff), "```"])
    if run_url:
        lines.extend(["", f"**Run:** {run_url}"])
    lines.extend(["", "_Auto-managed by `make check-retailer-drift`._"])
    return "\n".join(lines)


def _pretty_json(payload: Any) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True)


class GitHubIssueClient:
    def __init__(
        self,
        *,
        token: str,
        repo: GitHubRepo,
        dry_run: bool = False,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._token = token
        self._repo = repo
        self._dry_run = dry_run
        self._client = http_client or httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GitHubIssueClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def ensure_label(self, name: str = "retailer-drift", color: str = "d93f0b") -> None:
        if self._dry_run:
            return
        response = self._client.get(f"/repos/{self._repo.slug}/labels/{quote(name, safe='')}")
        if response.status_code == 404:
            self._client.post(
                f"/repos/{self._repo.slug}/labels",
                json={"name": name, "color": color, "description": "Retailer scraper drift or block alert"},
            )

    def find_open_issue(self, slug: str) -> dict[str, Any] | None:
        query = quote(f'repo:{self._repo.slug} label:retailer-drift is:issue is:open "[retailer-drift] {slug}"')
        response = self._client.get(f"/search/issues?q={query}&per_page=5")
        response.raise_for_status()
        items = response.json().get("items", [])
        for item in items:
            title = str(item.get("title", ""))
            match = _ISSUE_TITLE_RE.match(title)
            if match and match.group("slug") == slug:
                return item
        return None

    def sync_result(
        self,
        result: DriftCheckResult,
        *,
        run_url: str | None = None,
    ) -> str:
        if result.status == "ok":
            return self._close_if_open(result.slug, run_url=run_url)
        kind: IssueStatusKind
        if result.status == "blocked":
            kind = "blocked"
        elif result.status == "shape_mismatch":
            kind = "shape_mismatch"
        else:
            kind = "error"
        return self._open_or_update(result, kind=kind, run_url=run_url)

    def _close_if_open(self, slug: str, *, run_url: str | None) -> str:
        if self._dry_run:
            return f"dry-run would close open drift issue for {slug} if present"
        issue = self.find_open_issue(slug)
        if issue is None:
            return f"{slug}: no open drift issue"
        issue_number = issue["number"]
        comment = "Drift check passed. Auto-closed."
        if run_url:
            comment += f" Run: {run_url}"
        self._client.post(
            f"/repos/{self._repo.slug}/issues/{issue_number}/comments",
            json={"body": comment},
        )
        self._client.patch(
            f"/repos/{self._repo.slug}/issues/{issue_number}",
            json={"state": "closed"},
        )
        return f"{slug}: closed issue #{issue_number}"

    def _open_or_update(
        self,
        result: DriftCheckResult,
        *,
        kind: IssueStatusKind,
        run_url: str | None,
    ) -> str:
        if self._dry_run:
            return f"dry-run would create issue for {result.slug}"
        title = issue_title(result.slug, kind)
        body = format_issue_body(result, run_url=run_url)
        existing = self.find_open_issue(result.slug)
        if existing is None:
            response = self._client.post(
                f"/repos/{self._repo.slug}/issues",
                json={"title": title, "body": body, "labels": ["retailer-drift"]},
            )
            response.raise_for_status()
            number = response.json()["number"]
            return f"{result.slug}: opened issue #{number}"
        issue_number = existing["number"]
        if existing.get("title") != title:
            self._client.patch(
                f"/repos/{self._repo.slug}/issues/{issue_number}",
                json={"title": title},
            )
        self._client.post(
            f"/repos/{self._repo.slug}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return f"{result.slug}: updated issue #{issue_number}"
