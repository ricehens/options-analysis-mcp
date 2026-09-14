import pytest

from options_analysis.providers import HistoricalDataProvider, MarketDataProvider
from options_analysis.providers.fake import FakeProvider
from tests.contract.provider_contract import assert_market_data_provider_contract


@pytest.mark.asyncio
async def test_fake_provider_satisfies_market_data_contract() -> None:
    provider = FakeProvider()

    assert isinstance(provider, MarketDataProvider)
    assert isinstance(provider, HistoricalDataProvider)
    await assert_market_data_provider_contract(provider)
