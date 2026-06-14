"""Scraper exception hierarchy.

Maps to ``product_listings.scrape_status`` values for T2.5 translation:

- ``ok`` — successful scrape (no exception).
- ``failing`` — ``ScrapeParseError``, ``ScrapeTimeoutError``, ``FixtureNotFoundError``,
  ``NotCanadianListingError``, ``RetailerNotSupportedError``.
- ``blocked`` — ``ScrapeBlockedError``, ``NetworkBlockedInFixturesError``.  # pragma: allowlist secret
- Config/registry errors (``ScraperConfigError``, ``RetailerAlreadyRegisteredError``)
  are raised before a listing row is written.
"""

from __future__ import annotations


class ScraperError(Exception):
    """Base class for all scraper errors."""

    def __init__(
        self,
        message: str,
        *,
        retailer_slug: str | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retailer_slug = retailer_slug
        self.url = url


class ScraperConfigError(ScraperError):
    """Invalid scraper configuration (e.g. unknown scraper mode env var)."""


class RetailerNotSupportedError(ScraperError):
    """URL matched no registry entry and no generic fallback is registered."""


class RetailerAlreadyRegisteredError(ScraperError):
    """Attempted to register a retailer slug that is already registered."""


class NotCanadianListingError(ScraperError):
    """Listing currency is not CAD (checked by callers per PRD §7.2)."""


class ScrapeBlockedError(ScraperError):
    """Retailer blocked the request (403/429/CAPTCHA/Cloudflare)."""


class ScrapeParseError(ScraperError):
    """Response data was missing or could not be parsed."""


class ScrapeTimeoutError(ScraperError):
    """Request timed out before a response was received."""


class FixtureNotFoundError(ScraperError):
    """Fixture file not found on disk."""


class NetworkBlockedInFixturesError(ScraperError):  # pragma: allowlist secret
    """Outbound network request blocked because scraper mode is fixture-mode."""
