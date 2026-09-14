"""Reusable assertions for every MarketDataProvider implementation."""

from datetime import date

from options_analysis.providers import MarketDataProvider, OptionChainQuery


async def assert_market_data_provider_contract(
    provider: MarketDataProvider,
) -> None:
    descriptor = provider.descriptor
    status = provider.status()
    assert status.descriptor == descriptor
    assert status.configured is True
    assert status.ready is True

    quote = await provider.get_underlying_quote("spy")
    assert quote.provider_id == descriptor.provider_id
    assert quote.instrument.provider_id == descriptor.provider_id
    assert quote.instrument.symbol == "SPY"
    assert quote.as_of.tzinfo is not None
    assert quote.received_at.tzinfo is not None

    expirations = await provider.get_option_expirations("SPY")
    assert expirations == tuple(sorted(expirations))
    assert all(isinstance(expiration, date) for expiration in expirations)

    chain = await provider.get_option_chain(
        OptionChainQuery(underlying_symbol="SPY", limit=4)
    )
    assert chain.provider_id == descriptor.provider_id
    assert chain.underlying_symbol == "SPY"
    assert len(chain.contracts) == 4
    assert all(item.provider_id == descriptor.provider_id for item in chain.contracts)

    symbols = tuple(item.instrument.provider_symbol for item in chain.contracts[:2])
    selected = await provider.get_option_quotes(symbols)
    assert tuple(item.instrument.provider_symbol for item in selected) == symbols
