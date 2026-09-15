"""Built-in technical-indicator calculators over canonical price bars."""

from decimal import Decimal

from options_analysis.domain import (
    IndicatorChartRole,
    IndicatorValueUnit,
    PriceBar,
    TechnicalIndicatorDefinition,
    TechnicalIndicatorPoint,
    TechnicalIndicatorSeries,
)


class SimpleMovingAverageIndicator:
    """Arithmetic mean of closing prices over a bounded rolling window."""

    @property
    def definition(self) -> TechnicalIndicatorDefinition:
        return TechnicalIndicatorDefinition(
            indicator_id="sma",
            display_name="Simple moving average",
            description=(
                "Arithmetic mean of the previous N closing prices, including "
                "the current bar."
            ),
            chart_role=IndicatorChartRole.PRICE_OVERLAY,
            value_unit=IndicatorValueUnit.PRICE,
            argument_syntax="sma:<window>, where window is 2 through 500",
            example_specs=("sma:10", "sma:20", "sma:50"),
        )

    def calculate(
        self, bars: tuple[PriceBar, ...], spec: str
    ) -> TechnicalIndicatorSeries:
        parts = spec.split(":")
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError("SMA specification must use sma:<window>")
        window = int(parts[1])
        if not 2 <= window <= 500:
            raise ValueError("SMA window must be between 2 and 500")

        running_total = Decimal()
        closes: list[Decimal] = []
        points: list[TechnicalIndicatorPoint] = []
        for bar in bars:
            closes.append(bar.close)
            running_total += bar.close
            if len(closes) > window:
                running_total -= closes[-window - 1]
            if len(closes) >= window:
                points.append(
                    TechnicalIndicatorPoint(
                        timestamp=bar.start,
                        value=running_total / Decimal(window),
                    )
                )

        return TechnicalIndicatorSeries(
            indicator_id="sma",
            spec=f"sma:{window}",
            display_name=f"SMA {window}",
            chart_role=IndicatorChartRole.PRICE_OVERLAY,
            value_unit=IndicatorValueUnit.PRICE,
            parameters={"window": window},
            source_fields=("close",),
            points=tuple(points),
        )
