"""Service factory helpers for wiring production providers."""

from __future__ import annotations

from core.settings import Settings, get_settings
from db.supabase_client import get_service_role_client
from services.categorizer import DefaultCategorizer
from services.fx_cache_service import CachedFxService
from services.gemini import GeminiFlashLlmProvider
from services.llm import LlmProvider, NoOpLlmProvider
from services.mail import MailService, NoOpMailService
from services.resend_mail import ResendMailService


def build_retailer_default_categories() -> dict[str, str]:
    from scrapers.bestbuy_ca import register_bestbuy_ca
    from scrapers.generic import register_generic
    from scrapers.palmisleskate import register_palmisleskate
    from scrapers.registry import all_retailers
    from scrapers.tikiroomskate import register_tikiroomskate

    register_generic()
    register_bestbuy_ca()
    register_palmisleskate()
    register_tikiroomskate()
    return {entry.slug: entry.default_category for entry in all_retailers()}


def get_llm_provider(settings: Settings | None = None) -> LlmProvider:
    settings = settings or get_settings()
    if settings.gemini_api_key.strip():
        return GeminiFlashLlmProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            default_timeout_s=settings.gemini_categorize_timeout_s,
            discover_timeout_s=settings.gemini_discover_timeout_s,
        )
    return NoOpLlmProvider()


def get_categorizer(settings: Settings | None = None) -> DefaultCategorizer:
    settings = settings or get_settings()
    return DefaultCategorizer(
        get_llm_provider(settings),
        retailer_defaults=build_retailer_default_categories(),
        categorize_timeout_s=settings.gemini_categorize_timeout_s,
    )


def get_fx_service(settings: Settings | None = None) -> CachedFxService:
    settings = settings or get_settings()
    return CachedFxService(get_service_role_client(), settings=settings)


def get_mail_service(settings: Settings | None = None) -> MailService:
    settings = settings or get_settings()
    if settings.resend_api_key.strip():
        return ResendMailService(settings)
    return NoOpMailService()
