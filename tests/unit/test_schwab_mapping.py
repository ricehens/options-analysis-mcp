import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from options_analysis.domain import AssetType, PutCall
from options_analysis.providers import OptionChainQuery, PriceHistoryQuery
from options_analysis.providers.errors import ProviderResponseSchemaError
from options_analysis.providers.schwab.mapping import SchwabMapper

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures" / "schwab"


def load_fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def mapper() -> SchwabMapper:
    return SchwabMapper(clock=lambda: NOW)


def test_maps_equity_and_detailed_option_quotes() -> None:
    payload = load_fixture("quotes.json")

    equity = mapper().quote(payload, "spy")
    option = mapper().option_quotes(payload, ("SPY300118C00095000",))[0]

    assert equity.instrument.asset_type is AssetType.ETF
    assert equity.mark == Decimal("100.0")
    assert equity.warnings == ()
    assert option.instrument.option is not None
    assert option.instrument.option.put_call is PutCall.CALL
    assert option.instrument.option.expiration_date == date(2030, 1, 18)
    assert option.instrument.option.strike == Decimal("95")
    assert option.greeks is not None
    assert option.greeks.delta == Decimal("0.62")
    assert option.open_interest == 1200
    assert option.implied_volatility == Decimal("0.24")
    assert "schwab.realtime" in option.provider_extensions


def test_maps_expirations_and_filtered_chain() -> None:
    mapped = mapper()
    expirations = mapped.expirations(load_fixture("expirations.json"))
    chain = mapped.option_chain(
        load_fixture("chain.json"),
        OptionChainQuery(
            underlying_symbol="SPY",
            put_call=PutCall.CALL,
            strike_from=Decimal("95"),
            strike_to=Decimal("95"),
            limit=10,
        ),
    )

    assert expirations == (date(2030, 1, 18), date(2030, 2, 15))
    assert len(chain.contracts) == 1
    assert chain.contracts[0].instrument.symbol == "SPY300118C00095000"
    assert chain.underlying_quote is not None
    assert chain.underlying_quote.mark == Decimal("100.0")


def test_partial_and_empty_chains_remain_visible() -> None:
    mapped = mapper()
    partial = mapped.option_chain(
        load_fixture("partial_chain.json"),
        OptionChainQuery(underlying_symbol="SPY"),
    )
    empty = mapped.option_chain(
        {"symbol": "SPY", "callExpDateMap": {}, "putExpDateMap": {}},
        OptionChainQuery(underlying_symbol="SPY"),
    )

    partial_codes = {warning.code for warning in partial.warnings}
    quote_codes = {warning.code for warning in partial.contracts[0].warnings}
    assert partial_codes == {"partial_response"}
    assert {"crossed_market", "mark_outside_market", "missing_greeks"} <= quote_codes
    assert {warning.code for warning in empty.warnings} == {"empty_chain"}


def test_maps_price_history_and_rejects_schema_drift() -> None:
    query = PriceHistoryQuery(
        symbol="SPY",
        start=datetime(2026, 9, 13, tzinfo=UTC),
        end=datetime(2026, 9, 15, tzinfo=UTC),
        resolution="1d",
    )

    bars = mapper().price_history(load_fixture("price_history.json"), query)
    assert len(bars) == 2
    assert bars[1].close == Decimal("101.0")

    with pytest.raises(ProviderResponseSchemaError):
        mapper().price_history({"candles": []}, query)


def test_schema_drift_reports_field_paths_without_response_body() -> None:
    with pytest.raises(ProviderResponseSchemaError) as caught:
        mapper().quote(
            {"SPY": {"assetMainType": "EQUITY", "privateValue": "do-not-copy"}},
            "SPY",
        )

    assert caught.value.field_paths == ("SPY.symbol",)
    assert "do-not-copy" not in str(caught.value)
