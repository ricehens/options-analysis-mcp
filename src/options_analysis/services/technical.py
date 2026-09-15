"""Discovery and execution service for provider-neutral technical indicators."""

import re
from typing import Protocol

from options_analysis.domain import (
    PriceBar,
    TechnicalIndicatorDefinition,
    TechnicalIndicatorSeries,
)

_INDICATOR_ID = re.compile(r"^[a-z][a-z0-9_-]*$")


class TechnicalIndicatorCalculator(Protocol):
    @property
    def definition(self) -> TechnicalIndicatorDefinition: ...

    def calculate(
        self, bars: tuple[PriceBar, ...], spec: str
    ) -> TechnicalIndicatorSeries: ...


class TechnicalIndicatorRegistry:
    """Explicit registry; adding a calculator does not change market providers."""

    def __init__(self) -> None:
        self._calculators: dict[str, TechnicalIndicatorCalculator] = {}

    def register(self, calculator: TechnicalIndicatorCalculator) -> None:
        indicator_id = calculator.definition.indicator_id
        if indicator_id in self._calculators:
            raise ValueError(
                f"technical indicator {indicator_id!r} is already registered"
            )
        self._calculators[indicator_id] = calculator

    def get(self, indicator_id: str) -> TechnicalIndicatorCalculator:
        try:
            return self._calculators[indicator_id]
        except KeyError as error:
            raise ValueError(f"unknown technical indicator: {indicator_id}") from error

    def definitions(self) -> tuple[TechnicalIndicatorDefinition, ...]:
        return tuple(
            self._calculators[indicator_id].definition
            for indicator_id in sorted(self._calculators)
        )


class TechnicalIndicatorService:
    MAX_INDICATORS = 8
    MAX_BARS = 10_000

    def __init__(self, registry: TechnicalIndicatorRegistry) -> None:
        self._registry = registry

    def list_definitions(self) -> tuple[TechnicalIndicatorDefinition, ...]:
        return self._registry.definitions()

    def calculate(
        self, bars: tuple[PriceBar, ...], specs: tuple[str, ...]
    ) -> tuple[TechnicalIndicatorSeries, ...]:
        normalized_specs = tuple(
            dict.fromkeys(spec.strip().lower() for spec in specs if spec.strip())
        )
        if len(normalized_specs) > self.MAX_INDICATORS:
            raise ValueError(
                f"at most {self.MAX_INDICATORS} technical indicators may be requested"
            )
        if len(bars) > self.MAX_BARS:
            raise ValueError(f"at most {self.MAX_BARS} price bars may be analyzed")
        ordered = tuple(sorted(bars, key=lambda bar: bar.start))
        results: list[TechnicalIndicatorSeries] = []
        for spec in normalized_specs:
            indicator_id = spec.partition(":")[0]
            if not _INDICATOR_ID.fullmatch(indicator_id):
                raise ValueError("technical indicator ID is invalid")
            results.append(self._registry.get(indicator_id).calculate(ordered, spec))
        return tuple(results)
