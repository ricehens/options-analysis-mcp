"""Provider-neutral inputs and results for position analysis."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import Field, field_validator, model_validator

from options_analysis.domain._base import DomainModel
from options_analysis.domain.instruments import AssetType
from options_analysis.domain.market_data import DataQualityWarning
from options_analysis.domain.positions import PositionLeg


class ValuationMode(StrEnum):
    MARK = "mark"
    MIDPOINT = "midpoint"
    LIQUIDATION = "liquidation"


class PositionRequestLeg(DomainModel):
    """A user position keyed by a symbol understood by the selected provider."""

    symbol: str = Field(min_length=1)
    asset_type: AssetType
    quantity: Decimal
    average_open_price: Decimal | None = Field(default=None, ge=Decimal("0"))

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("quantity")
    @classmethod
    def quantity_is_nonzero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("position quantity must be nonzero")
        return value

    @model_validator(mode="after")
    def supported_asset_type(self) -> Self:
        if self.asset_type not in {AssetType.EQUITY, AssetType.ETF, AssetType.OPTION}:
            raise ValueError("position analysis supports equity, ETF, or option legs")
        return self


class GreekExposure(DomainModel):
    value: Decimal
    complete: bool
    missing_symbols: tuple[str, ...] = ()


class AggregateGreeks(DomainModel):
    delta: GreekExposure
    gamma: GreekExposure
    theta: GreekExposure
    vega: GreekExposure
    rho: GreekExposure


class PayoffPoint(DomainModel):
    underlying_price: Decimal = Field(ge=Decimal("0"))
    position_value: Decimal
    profit_loss: Decimal | None = None


class ScenarioPoint(DomainModel):
    underlying_price: Decimal = Field(ge=Decimal("0"))
    underlying_change: Decimal
    estimated_profit_loss: Decimal | None
    method: str


class PositionAnalysis(DomainModel):
    provider_id: str
    valuation_mode: ValuationMode
    positions: tuple[PositionLeg, ...]
    underlying_symbol: str | None
    underlying_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    net_market_value: Decimal | None
    net_cost_basis: Decimal | None
    aggregate_greeks: AggregateGreeks
    expiration_date: date | None
    payoff_points: tuple[PayoffPoint, ...] = ()
    break_even_prices: tuple[Decimal, ...] = ()
    max_profit: Decimal | None = None
    max_profit_bounded: bool | None = None
    max_loss: Decimal | None = None
    max_loss_bounded: bool | None = None
    scenarios: tuple[ScenarioPoint, ...] = ()
    assumptions: tuple[str, ...] = ()
    warnings: tuple[DataQualityWarning, ...] = ()
