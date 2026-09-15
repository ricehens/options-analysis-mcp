"""Generate a deterministic canonical bundle for offline replay exercises."""

from datetime import timedelta

from options_analysis.providers import OptionChainQuery, PriceHistoryQuery
from options_analysis.providers.fake import FakeProvider
from options_analysis.providers.replay.models import (
    ReplayBundle,
    ReplayHistorySeries,
    ReplaySource,
    ReplaySymbolSnapshot,
)

_LOOKBACKS = {
    "1m": timedelta(days=1),
    "5m": timedelta(days=7),
    "1d": timedelta(days=365),
    "1w": timedelta(days=365 * 5),
    "1mo": timedelta(days=365 * 20),
}


async def create_sample_bundle(symbol: str = "SPY") -> ReplayBundle:
    """Create synthetic data using the same canonical models as live adapters."""

    normalized = symbol.strip().upper()
    provider = FakeProvider()
    quote = await provider.get_underlying_quote(normalized)
    chain = await provider.get_option_chain(
        OptionChainQuery(underlying_symbol=normalized, limit=100)
    )
    history: list[ReplayHistorySeries] = []
    for resolution, lookback in _LOOKBACKS.items():
        bars = await provider.get_price_history(
            PriceHistoryQuery(
                symbol=normalized,
                start=quote.as_of - lookback,
                end=quote.as_of,
                resolution=resolution,
            )
        )
        history.append(ReplayHistorySeries(resolution=resolution, bars=bars))
    return ReplayBundle(
        created_at=quote.received_at,
        source=ReplaySource(
            label="Built-in deterministic synthetic sample",
            original_provider_id="fake",
            acquired_at=quote.as_of,
            usage_notes=(
                "Generated locally; contains no broker or licensed market data."
            ),
        ),
        symbols=(
            ReplaySymbolSnapshot(
                symbol=normalized,
                underlying_quote=quote,
                option_chain=chain,
                price_history=tuple(history),
            ),
        ),
    )
