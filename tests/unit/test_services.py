import pytest

from options_analysis.bootstrap import build_application
from options_analysis.config import AppSettings
from options_analysis.domain import Quote
from options_analysis.providers import (
    AuthenticationState,
    Capability,
    ProviderRegistry,
    ProviderRouter,
)
from options_analysis.providers.fake import FakeProvider
from options_analysis.services import MarketDataService
from options_analysis.services.cache import TTLCache


class CountingFakeProvider(FakeProvider):
    def __init__(self) -> None:
        self.quote_calls = 0

    async def get_underlying_quote(self, symbol: str) -> Quote:
        self.quote_calls += 1
        return await super().get_underlying_quote(symbol)


@pytest.mark.asyncio
async def test_market_data_service_uses_default_fake_provider() -> None:
    application = build_application(AppSettings(_env_file=None))

    quote = await application.market_data_service.get_underlying_quote(" spy ")

    assert quote.provider_id == "fake"
    assert quote.instrument.symbol == "SPY"
    assert quote.mark is not None


def test_provider_service_lists_capabilities_without_secrets() -> None:
    application = build_application(AppSettings(_env_file=None))

    status = application.provider_service.list_statuses()[0]

    assert Capability.OPTION_CHAINS in status.descriptor.capabilities
    assert "credential" not in status.model_dump_json().lower()


def test_provider_service_reports_generic_auth_status() -> None:
    application = build_application(AppSettings(_env_file=None))

    status = application.provider_service.auth_status("fake")

    assert status.state is AuthenticationState.NOT_REQUIRED
    assert status.authorized is True


@pytest.mark.asyncio
async def test_market_data_service_caches_by_provider_and_normalized_symbol() -> None:
    provider = CountingFakeProvider()
    registry = ProviderRegistry(("fake",))
    registry.register(provider)
    service = MarketDataService(
        ProviderRouter(registry, default_market_data_provider="fake"),
        quote_cache=TTLCache(ttl_seconds=1, max_entries=10),
    )

    first = await service.get_underlying_quote(" spy ")
    second = await service.get_underlying_quote("SPY")

    assert first is second
    assert provider.quote_calls == 1
