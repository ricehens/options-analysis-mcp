"""Market-data use cases independent of concrete providers."""

from options_analysis.domain import Quote
from options_analysis.providers import ProviderRouter


class MarketDataService:
    def __init__(self, router: ProviderRouter) -> None:
        self._router = router

    async def get_underlying_quote(
        self, symbol: str, provider_id: str | None = None
    ) -> Quote:
        provider = self._router.market_data(provider_id)
        return await provider.get_underlying_quote(symbol)
