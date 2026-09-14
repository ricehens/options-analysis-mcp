from decimal import Decimal

import pytest

from options_analysis.bootstrap import build_application
from options_analysis.config import AppSettings
from options_analysis.domain import (
    AssetType,
    PositionRequestLeg,
    ValuationMode,
)
from options_analysis.providers.fake import FakeProvider
from options_analysis.services.analysis import PositionAnalysisService


def option_leg(
    symbol: str, quantity: str, open_price: str | None
) -> PositionRequestLeg:
    return PositionRequestLeg(
        symbol=symbol,
        asset_type=AssetType.OPTION,
        quantity=Decimal(quantity),
        average_open_price=(Decimal(open_price) if open_price is not None else None),
    )


@pytest.mark.asyncio
async def test_vertical_call_spread_matches_hand_calculation() -> None:
    service = build_application(AppSettings(_env_file=None)).position_analysis_service

    result = await service.analyze(
        (
            option_leg("SPY300118C00095000", "1", "6"),
            option_leg("SPY300118C00100000", "-1", "3"),
        )
    )

    assert result.provider_id == "fake"
    assert result.net_cost_basis == Decimal("300")
    assert result.break_even_prices == (Decimal("98"),)
    assert result.max_profit == Decimal("200")
    assert result.max_profit_bounded is True
    assert result.max_loss == Decimal("-300")
    assert result.max_loss_bounded is True
    assert result.aggregate_greeks.delta.value == 0
    assert result.aggregate_greeks.gamma.value == 0
    assert all(point.estimated_profit_loss == 0 for point in result.scenarios)


@pytest.mark.asyncio
async def test_long_and_short_call_report_unbounded_side() -> None:
    service = build_application(AppSettings(_env_file=None)).position_analysis_service

    long_call = await service.analyze((option_leg("SPY300118C00095000", "1", "6"),))
    short_call = await service.analyze((option_leg("SPY300118C00100000", "-1", "3"),))

    assert long_call.break_even_prices == (Decimal("101"),)
    assert long_call.max_profit is None
    assert long_call.max_profit_bounded is False
    assert long_call.max_loss == Decimal("-600")
    assert long_call.max_loss_bounded is True
    assert short_call.max_profit == Decimal("300")
    assert short_call.max_profit_bounded is True
    assert short_call.max_loss is None
    assert short_call.max_loss_bounded is False


@pytest.mark.asyncio
async def test_liquidation_mode_uses_bid_for_long_and_ask_for_short() -> None:
    service = build_application(AppSettings(_env_file=None)).position_analysis_service

    result = await service.analyze(
        (
            option_leg("SPY300118C00095000", "1", None),
            option_leg("SPY300118C00100000", "-1", None),
        ),
        valuation_mode=ValuationMode.LIQUIDATION,
    )

    assert result.net_market_value == Decimal("-260")
    assert result.net_cost_basis is None
    assert result.break_even_prices == ()
    assert {warning.code for warning in result.warnings} >= {"missing_cost_basis"}


@pytest.mark.asyncio
async def test_calendar_position_omits_exact_expiration_payoff() -> None:
    service = build_application(AppSettings(_env_file=None)).position_analysis_service

    result = await service.analyze(
        (
            option_leg("SPY300118C00100000", "1", "5"),
            option_leg("SPY300215C00100000", "-1", "4"),
        )
    )

    assert result.expiration_date is None
    assert result.payoff_points == ()
    assert "multiple_expirations" in {warning.code for warning in result.warnings}


@pytest.mark.asyncio
async def test_scenario_moves_are_bounded() -> None:
    service = build_application(AppSettings(_env_file=None)).position_analysis_service

    with pytest.raises(ValueError, match="greater than -1"):
        await service.analyze(
            (option_leg("SPY300118C00100000", "1", "5"),),
            scenario_moves=(Decimal("-1"),),
        )


@pytest.mark.asyncio
async def test_zero_liquidation_bid_is_not_replaced_by_mark() -> None:
    quote = (await FakeProvider().get_option_quotes(("SPY300118C00100000",)))[0]
    zero_bid = quote.model_copy(update={"bid": Decimal("0")})

    price = PositionAnalysisService._valuation_price(
        zero_bid, Decimal("1"), ValuationMode.LIQUIDATION
    )

    assert price == 0


@pytest.mark.asyncio
async def test_multiple_underlyings_do_not_produce_one_factor_scenarios() -> None:
    service = build_application(AppSettings(_env_file=None)).position_analysis_service
    legs = (
        PositionRequestLeg(
            symbol="SPY",
            asset_type=AssetType.ETF,
            quantity=Decimal("10"),
            average_open_price=Decimal("90"),
        ),
        PositionRequestLeg(
            symbol="AAPL",
            asset_type=AssetType.EQUITY,
            quantity=Decimal("5"),
            average_open_price=Decimal("80"),
        ),
    )

    result = await service.analyze(legs)

    assert result.underlying_symbol is None
    assert result.underlying_price is None
    assert result.scenarios == ()
    assert "multiple_underlyings" in {warning.code for warning in result.warnings}
