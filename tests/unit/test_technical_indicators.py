from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from options_analysis.analytics.indicators import SimpleMovingAverageIndicator
from options_analysis.domain import AssetType, Instrument, PriceBar
from options_analysis.services import (
    TechnicalIndicatorRegistry,
    TechnicalIndicatorService,
)


def sample_bars(closes: tuple[str, ...]) -> tuple[PriceBar, ...]:
    instrument = Instrument(
        asset_type=AssetType.EQUITY,
        symbol="SPY",
        provider_id="fake",
        provider_symbol="SPY",
    )
    start = datetime(2026, 9, 1, tzinfo=UTC)
    return tuple(
        PriceBar(
            provider_id="fake",
            instrument=instrument,
            start=start + timedelta(days=index),
            end=start + timedelta(days=index + 1),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=1_000,
        )
        for index, close in enumerate(closes)
    )


def service() -> TechnicalIndicatorService:
    registry = TechnicalIndicatorRegistry()
    registry.register(SimpleMovingAverageIndicator())
    return TechnicalIndicatorService(registry)


def test_simple_moving_average_uses_current_and_previous_closes() -> None:
    result = service().calculate(sample_bars(("1", "2", "3", "4", "5")), ("sma:3",))

    assert len(result) == 1
    assert result[0].display_name == "SMA 3"
    assert result[0].parameters == {"window": 3}
    assert tuple(point.value for point in result[0].points) == (
        Decimal("2"),
        Decimal("3"),
        Decimal("4"),
    )
    assert result[0].points[0].timestamp == datetime(2026, 9, 3, tzinfo=UTC)


def test_registry_discovers_indicator_and_service_deduplicates_specs() -> None:
    technical = service()

    definitions = technical.list_definitions()
    results = technical.calculate(sample_bars(("1", "2", "3")), (" SMA:2 ", "sma:2"))

    assert definitions[0].indicator_id == "sma"
    assert definitions[0].example_specs == ("sma:20", "sma:50")
    assert len(results) == 1


@pytest.mark.parametrize("spec", ("sma", "sma:one", "sma:1", "sma:501", "rsi:14"))
def test_invalid_or_unknown_indicator_specs_fail_explicitly(spec: str) -> None:
    with pytest.raises(ValueError):
        service().calculate(sample_bars(("1", "2", "3")), (spec,))


def test_service_orders_input_bars_before_calculating() -> None:
    bars = sample_bars(("1", "2", "3"))

    result = service().calculate(tuple(reversed(bars)), ("sma:2",))[0]

    assert tuple(point.value for point in result.points) == (
        Decimal("1.5"),
        Decimal("2.5"),
    )
