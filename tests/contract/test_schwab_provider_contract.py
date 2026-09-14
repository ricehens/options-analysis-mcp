import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from options_analysis.config import AppSettings
from options_analysis.providers import MarketDataProvider, PriceHistoryQuery
from options_analysis.providers.schwab import build_schwab_provider
from options_analysis.providers.schwab.tokens import OAuthToken, TokenStore
from tests.contract.provider_contract import assert_market_data_provider_contract

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures" / "schwab"


def load_fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
async def test_schwab_adapter_passes_shared_market_data_contract(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        fixtures = {
            "/marketdata/v1/quotes": "quotes.json",
            "/marketdata/v1/expirationchain": "expirations.json",
            "/marketdata/v1/chains": "chain.json",
        }
        if request.url.path == "/marketdata/v1/chains":
            assert request.url.params["fromDate"] == "2026-09-14"
            assert request.url.params["toDate"] == "2026-10-29"
            assert request.url.params["strikeCount"] == "2"
        return httpx.Response(200, json=load_fixture(fixtures[request.url.path]))

    token_path = tmp_path / "schwab-token.json"
    TokenStore(token_path).save(
        OAuthToken(
            access_token="synthetic-access",
            refresh_token="synthetic-refresh",
            expires_at=NOW + timedelta(hours=1),
        )
    )
    settings = AppSettings(
        _env_file=None,
        enabled_providers=("schwab",),
        default_market_data_provider="schwab",
        schwab_client_id=SecretStr("synthetic-client"),
        schwab_client_secret=SecretStr("synthetic-secret"),
        schwab_token_path=token_path,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = build_schwab_provider(settings, client=client, clock=lambda: NOW)
        assert isinstance(provider, MarketDataProvider)
        await assert_market_data_provider_contract(provider)


@pytest.mark.asyncio
async def test_schwab_adapter_maps_price_history(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/marketdata/v1/pricehistory"
        assert request.url.params["frequencyType"] == "daily"
        return httpx.Response(200, json=load_fixture("price_history.json"))

    token_path = tmp_path / "schwab-token.json"
    TokenStore(token_path).save(
        OAuthToken(
            access_token="synthetic-access",
            refresh_token="synthetic-refresh",
            expires_at=NOW + timedelta(hours=1),
        )
    )
    settings = AppSettings(
        _env_file=None,
        enabled_providers=("schwab",),
        default_market_data_provider="schwab",
        schwab_client_id=SecretStr("synthetic-client"),
        schwab_client_secret=SecretStr("synthetic-secret"),
        schwab_token_path=token_path,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = build_schwab_provider(settings, client=client, clock=lambda: NOW)
        bars = await provider.get_price_history(
            PriceHistoryQuery(
                symbol="SPY",
                start=datetime(2026, 9, 13, tzinfo=UTC),
                end=datetime(2026, 9, 15, tzinfo=UTC),
                resolution="1d",
            )
        )

    assert len(bars) == 2
    assert bars[0].instrument.symbol == "SPY"
    assert bars[0].close == 100
    assert bars[0].end - bars[0].start == timedelta(days=1)
