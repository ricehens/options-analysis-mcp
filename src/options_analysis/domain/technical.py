"""Provider-neutral technical-indicator discovery and result models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import Field, JsonValue, field_validator, model_validator

from options_analysis.domain._base import DomainModel, require_aware_datetime


class IndicatorChartRole(StrEnum):
    PRICE_OVERLAY = "price_overlay"
    LOWER_PANEL = "lower_panel"
    EVENT_MARKERS = "event_markers"


class IndicatorValueUnit(StrEnum):
    PRICE = "price"
    PERCENT = "percent"
    UNITLESS = "unitless"


class TechnicalIndicatorDefinition(DomainModel):
    indicator_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    chart_role: IndicatorChartRole
    value_unit: IndicatorValueUnit
    argument_syntax: str = Field(min_length=1, max_length=100)
    example_specs: tuple[str, ...] = Field(min_length=1, max_length=10)


class TechnicalIndicatorPoint(DomainModel):
    timestamp: datetime
    value: Decimal

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class TechnicalIndicatorSeries(DomainModel):
    indicator_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    spec: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=100)
    chart_role: IndicatorChartRole
    value_unit: IndicatorValueUnit
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    source_fields: tuple[str, ...] = ()
    points: tuple[TechnicalIndicatorPoint, ...] = Field(max_length=10_000)

    @model_validator(mode="after")
    def points_are_ordered(self) -> Self:
        timestamps = tuple(point.timestamp for point in self.points)
        if timestamps != tuple(sorted(timestamps)):
            raise ValueError("technical-indicator points must be time ordered")
        return self
