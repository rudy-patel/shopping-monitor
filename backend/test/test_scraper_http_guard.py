"""HTTP guard and import restriction tests."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from scrapers.exceptions import (
    NetworkBlockedInFixturesError,  # pragma: allowlist secret
    ScrapeBlockedError,
)
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


def _stub_curl_response(*, url: str = "https://www.bestbuy.ca/foo") -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.text = "<html>ok</html>"
    response.content = b"<html>ok</html>"
    response.headers = {"content-type": "text/html"}
    response.url = url
    return response


def test_live_mode_uses_curl_cffi(monkeypatch):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, "live")
    captured: dict[str, object] = {}

    def stub_get(url, **kwargs):
        captured["url"] = url
        captured["impersonate"] = kwargs.get("impersonate")
        captured["headers"] = kwargs.get("headers")
        return _stub_curl_response(url=url)

    fake_requests = MagicMock()
    fake_requests.get = stub_get
    monkeypatch.setitem(
        __import__("sys").modules,
        "curl_cffi",
        MagicMock(requests=fake_requests),
    )

    response = scraper_fetch(
        "https://www.bestbuy.ca/foo",
        retailer_slug="bestbuy_ca",
        timeout=5.0,
        headers={"User-Agent": "test-agent"},
    )

    assert response.status_code == 200
    assert response.body_text == "<html>ok</html>"
    assert captured["url"] == "https://www.bestbuy.ca/foo"
    assert captured["impersonate"] == "chrome"
    assert captured["headers"]["User-Agent"] == "test-agent"
    assert captured["headers"]["Accept-Language"] == "en-CA,en;q=0.9"


def test_curl_cffi_fallback_to_httpx(monkeypatch):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, "live")

    def fail_get(*_args, **_kwargs):
        raise RuntimeError("curl_cffi unavailable")

    fake_requests = MagicMock()
    fake_requests.get = fail_get
    monkeypatch.setitem(
        __import__("sys").modules,
        "curl_cffi",
        MagicMock(requests=fake_requests),
    )

    class StubResponse:
        status_code = 200
        text = "<html>httpx</html>"
        content = b"<html>httpx</html>"
        headers = {"content-type": "text/html"}
        url = "https://www.bestbuy.ca/foo"

    def stub_send(self, request, **kwargs):
        return StubResponse()

    monkeypatch.setattr(httpx.Client, "send", stub_send)
    response = scraper_fetch(
        "https://www.bestbuy.ca/foo",
        retailer_slug="bestbuy_ca",
    )
    assert response.body_text == "<html>httpx</html>"


def test_curl_cffi_blocked_raises(monkeypatch):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, "live")

    def stub_get(url, **kwargs):
        response = MagicMock()
        response.status_code = 403
        response.text = (
            "<html><title>Attention Required | Cloudflare</title>"
            "<body>cf-browser-verification</body></html>"
        )
        response.content = response.text.encode()
        response.headers = {}
        response.url = url
        return response

    fake_requests = MagicMock()
    fake_requests.get = stub_get
    monkeypatch.setitem(
        __import__("sys").modules,
        "curl_cffi",
        MagicMock(requests=fake_requests),
    )

    with pytest.raises(ScrapeBlockedError):
        scraper_fetch(
            "https://www.bestbuy.ca/foo",
            retailer_slug="bestbuy_ca",
        )


def test_record_mode_behaves_like_live(monkeypatch):
    monkeypatch.setenv(SCRAPER_MODE_ENV_VAR, "record")
    captured: dict[str, object] = {}

    def stub_get(url, **kwargs):
        captured["url"] = url
        return _stub_curl_response(url=url)

    fake_requests = MagicMock()
    fake_requests.get = stub_get
    monkeypatch.setitem(
        __import__("sys").modules,
        "curl_cffi",
        MagicMock(requests=fake_requests),
    )

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
