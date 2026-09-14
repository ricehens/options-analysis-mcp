"""Market-data use cases independent of concrete providers."""

from datetime import date

from options_analysis.domain import OptionChain, PriceBar, Quote
from options_analysis.providers import (
    Capability,
    OptionChainQuery,
    PriceHistoryQuery,
    ProviderRouter,
)


class MarketDataService:
    def __init__(self, router: ProviderRouter) -> None:
        self._router = router

    async def get_underlying_quote(
        self, symbol: str, provider_id: str | None = None
    ) -> Quote:
        provider = self._router.market_data(provider_id)
        return await provider.get_underlying_quote(symbol)

    async def get_option_expirations(
        self, underlying_symbol: str, provider_id: str | None = None
    ) -> tuple[date, ...]:
        provider = self._router.market_data(
            provider_id, capability=Capability.OPTION_EXPIRATIONS
        )
        return await provider.get_option_expirations(underlying_symbol)

    async def get_option_chain(
        self, query: OptionChainQuery, provider_id: str | None = None
    ) -> OptionChain:
        provider = self._router.market_data(
            provider_id, capability=Capability.OPTION_CHAINS
        )
        return await provider.get_option_chain(query)

    async def get_option_quotes(
        self, symbols: tuple[str, ...], provider_id: str | None = None
    ) -> tuple[Quote, ...]:
        if not symbols:
            raise ValueError("at least one option symbol is required")
        if len(symbols) > 100:
            raise ValueError("at most 100 option symbols may be requested")
        provider = self._router.market_data(
            provider_id, capability=Capability.OPTION_QUOTES
        )
        return await provider.get_option_quotes(symbols)

    async def get_price_history(
        self, query: PriceHistoryQuery, provider_id: str | None = None
    ) -> tuple[PriceBar, ...]:
        provider = self._router.historical(provider_id)
        return await provider.get_price_history(query)
