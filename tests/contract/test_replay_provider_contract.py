from datetime import timedelta

import pytest

from options_analysis.providers import (
    HistoricalDataProvider,
    MarketDataProvider,
    OptionChainQuery,
    PriceHistoryQuery,
)
from options_analysis.providers.replay import ReplayProvider
from options_analysis.providers.replay.sample import create_sample_bundle
from tests.contract.provider_contract import assert_market_data_provider_contract


@pytest.mark.asyncio
async def test_replay_provider_satisfies_market_data_contract() -> None:
    provider = ReplayProvider(await create_sample_bundle())

    assert isinstance(provider, MarketDataProvider)
    assert isinstance(provider, HistoricalDataProvider)
    await assert_market_data_provider_contract(provider)


@pytest.mark.asyncio
async def test_replay_remaps_transport_provider_but_preserves_origin() -> None:
    provider = ReplayProvider(await create_sample_bundle())

    chain = await provider.get_option_chain(
        OptionChainQuery(underlying_symbol="SPY", strike_from="100", limit=3)
    )

    assert chain.provider_id == "replay"
    assert all(quote.provider_id == "replay" for quote in chain.contracts)
    assert all(
        quote.provider_extensions["replay.original_provider_id"] == "fake"
        for quote in chain.contracts
    )
    assert all(
        quote.instrument.option is not None and quote.instrument.option.strike >= 100
        for quote in chain.contracts
    )


@pytest.mark.asyncio
async def test_replay_history_uses_recorded_resolution_and_requested_window() -> None:
    bundle = await create_sample_bundle()
    provider = ReplayProvider(bundle)
    end = bundle.created_at

    bars = await provider.get_price_history(
        PriceHistoryQuery(
            symbol="SPY",
            start=end - timedelta(days=30),
            end=end,
            resolution="1d",
        )
    )

    assert 20 <= len(bars) <= 31
    assert all(bar.provider_id == "replay" for bar in bars)
    assert all(bar.end > end - timedelta(days=30) for bar in bars)
