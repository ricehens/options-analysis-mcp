"""Composition root; the only core module that selects concrete adapters."""

from dataclasses import dataclass

from options_analysis.config import AppSettings
from options_analysis.providers import ProviderRegistry, ProviderRouter
from options_analysis.providers.fake import FakeProvider
from options_analysis.providers.schwab import build_schwab_provider
from options_analysis.services import MarketDataService, ProviderService


@dataclass(frozen=True, slots=True)
class Application:
    settings: AppSettings
    registry: ProviderRegistry
    provider_service: ProviderService
    market_data_service: MarketDataService


def build_application(settings: AppSettings | None = None) -> Application:
    resolved_settings = settings or AppSettings()
    registry = ProviderRegistry(resolved_settings.enabled_providers)
    if "fake" in resolved_settings.enabled_providers:
        registry.register(FakeProvider())
    if "schwab" in resolved_settings.enabled_providers:
        registry.register(build_schwab_provider(resolved_settings))
    registry.load_entry_point_plugins()
    router = ProviderRouter(
        registry,
        default_market_data_provider=resolved_settings.default_market_data_provider,
    )
    return Application(
        settings=resolved_settings,
        registry=registry,
        provider_service=ProviderService(registry),
        market_data_service=MarketDataService(router),
    )
