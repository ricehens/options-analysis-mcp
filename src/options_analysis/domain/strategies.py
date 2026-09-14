"""Canonical strategy-template descriptions; never execution instructions."""

from decimal import Decimal
from enum import StrEnum

from pydantic import Field

from options_analysis.domain._base import DomainModel
from options_analysis.domain.instruments import AssetType, PutCall


class StrategyAction(StrEnum):
    BUY = "buy"
    SELL = "sell"


class StrategyOutlook(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    CUSTOM = "custom"


class StrategyLegRole(DomainModel):
    label: str = Field(min_length=1)
    asset_type: AssetType
    action: StrategyAction
    ratio: Decimal = Field(gt=Decimal("0"))
    put_call: PutCall | None = None
    strike_order: int | None = Field(default=None, ge=0)
    expiration_order: int | None = Field(default=None, ge=0)


class StrategyTemplate(DomainModel):
    template_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    outlook: StrategyOutlook
    same_expiration: bool
    legs: tuple[StrategyLegRole, ...]
