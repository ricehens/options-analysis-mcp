"""Composition root; the only core module that selects concrete adapters."""

from dataclasses import dataclass

from options_analysis.analytics.indicators import SimpleMovingAverageIndicator
from options_analysis.config import AppSettings
from options_analysis.providers import ProviderRegistry, ProviderRouter
from options_analysis.providers.fake import FakeProvider
from options_analysis.providers.replay import build_replay_provider
from options_analysis.providers.schwab import build_schwab_provider
from options_analysis.services import (
    MarketDataService,
    PositionAnalysisService,
    ProviderService,
    StrategyCatalogService,
    StrategyDraftService,
    TechnicalIndicatorRegistry,
    TechnicalIndicatorService,
    WatchlistService,
)
from options_analysis.services.cache import TTLCache
from options_analysis.storage import (
    SQLiteStrategyDraftRepository,
    SQLiteWatchlistRepository,
    default_state_db_path,
)


@dataclass(frozen=True, slots=True)
class Application:
    settings: AppSettings
    registry: ProviderRegistry
    provider_service: ProviderService
    market_data_service: MarketDataService
    position_analysis_service: PositionAnalysisService
    watchlist_service: WatchlistService
    strategy_catalog_service: StrategyCatalogService
    strategy_draft_service: StrategyDraftService
    technical_indicator_service: TechnicalIndicatorService


def build_application(settings: AppSettings | None = None) -> Application:
    resolved_settings = settings or AppSettings()
    registry = ProviderRegistry(resolved_settings.enabled_providers)
    if "fake" in resolved_settings.enabled_providers:
        registry.register(FakeProvider())
    if "replay" in resolved_settings.enabled_providers:
        registry.register(build_replay_provider(resolved_settings))
    if "schwab" in resolved_settings.enabled_providers:
        registry.register(build_schwab_provider(resolved_settings))
    registry.load_entry_point_plugins()
    router = ProviderRouter(
        registry,
        default_market_data_provider=resolved_settings.default_market_data_provider,
    )
    market_data = MarketDataService(
        router,
        quote_cache=TTLCache(
            ttl_seconds=resolved_settings.snapshot_cache_ttl_seconds,
            max_entries=resolved_settings.snapshot_cache_max_entries,
        ),
    )
    state_db_path = resolved_settings.state_db_path or default_state_db_path()
    indicator_registry = TechnicalIndicatorRegistry()
    indicator_registry.register(SimpleMovingAverageIndicator())
    return Application(
        settings=resolved_settings,
        registry=registry,
        provider_service=ProviderService(registry),
        market_data_service=market_data,
        position_analysis_service=PositionAnalysisService(market_data),
        watchlist_service=WatchlistService(SQLiteWatchlistRepository(state_db_path)),
        strategy_catalog_service=StrategyCatalogService(),
        strategy_draft_service=StrategyDraftService(
            SQLiteStrategyDraftRepository(state_db_path)
        ),
        technical_indicator_service=TechnicalIndicatorService(indicator_registry),
    )
