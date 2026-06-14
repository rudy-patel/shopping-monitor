"""HTTP guard and import restriction tests."""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest

from scrapers.exceptions import NetworkBlockedInFixturesError  # pragma: allowlist secret
from scrapers.http import scraper_fetch
from scrapers.mode import SCRAPER_MODE_ENV_VAR

_HTTP_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+httpx|import\s+httpx|import\s+curl_cffi|import\s+requests)\b",
    re.MULTILINE,
)


def test_fixture_mode_blocks_network(monkeypatch):
    monkeypatch.delenv(SCRAPER_MODE_ENV_VAR, raising=False)

    def fail_send(*_args, **_kwargs):
        pytest.fail("network must not be opened")

    monkeypatch.setattr(httpx.Client, "send", fail_send)
    with pytest.raises(NetworkBlockedInFixturesError):  # pragma: allowlist secret
        scraper_fetch(
            "https://www.bestbuy.ca/foo",
            retailer_slug="bestbuy_ca",
        )


def _stub_httpx_response(monkeypatch, *, mode: str) -> dict[str, object]:
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, mode)

    class StubResponse:
        status_code = 200
        text = "<html>ok</html>"
        content = b"<html>ok</html>"
        headers = {"content-type": "text/html"}
        url = "https://www.bestbuy.ca/foo"

    captured: dict[str, object] = {}

    original_init = httpx.Client.__init__

    def capturing_init(self, *args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return original_init(self, *args, **kwargs)

    def stub_send(self, request, **kwargs):
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return StubResponse()

    monkeypatch.setattr(httpx.Client, "__init__", capturing_init)
    monkeypatch.setattr(httpx.Client, "send", stub_send)
    return captured


def test_live_mode_delegates_to_httpx(monkeypatch):
    captured = _stub_httpx_response(monkeypatch, mode="live")
    response = scraper_fetch(
        "https://www.bestbuy.ca/foo",
        retailer_slug="bestbuy_ca",
        timeout=5.0,
        headers={"User-Agent": "test-agent"},
    )
    assert response.status_code == 200
    assert response.body_text == "<html>ok</html>"
    assert response.final_url == "https://www.bestbuy.ca/foo"
    assert captured["url"] == "https://www.bestbuy.ca/foo"
    assert captured["timeout"] == 5.0
    assert captured["headers"]["user-agent"] == "test-agent"


def test_record_mode_behaves_like_live(monkeypatch):
    captured = _stub_httpx_response(monkeypatch, mode="record")
    response = scraper_fetch(
        "https://www.bestbuy.ca/foo",
        retailer_slug="bestbuy_ca",
    )
    assert response.status_code == 200
    assert captured["url"] == "https://www.bestbuy.ca/foo"


def test_only_http_py_imports_http_clients():
    scrapers_dir = Path(__file__).resolve().parents[1] / "scrapers"
    allowed = {"http.py", "__init__.py"}
    offenders: list[str] = []
    for path in scrapers_dir.rglob("*.py"):
        if path.name in allowed:
            continue
        content = path.read_text(encoding="utf-8")
        if _HTTP_IMPORT_RE.search(content):
            offenders.append(str(path.relative_to(scrapers_dir.parent)))
    assert offenders == []
