"""Provider-neutral saved strategy definitions, separate from live quotes."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from options_analysis.domain._base import DomainModel, require_aware_datetime
from options_analysis.domain.instruments import AssetType
from options_analysis.domain.watchlists import normalize_watchlist_symbol


class StrategyDraftLeg(DomainModel):
    symbol: str = Field(min_length=1)
    provider_symbol: str = Field(min_length=1)
    asset_type: AssetType
    quantity: Decimal
    average_open_price: Decimal | None = Field(default=None, ge=Decimal("0"))

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("provider_symbol")
    @classmethod
    def normalize_provider_symbol(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("provider symbol must not be empty")
        return normalized

    @field_validator("quantity")
    @classmethod
    def quantity_is_nonzero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("strategy draft quantity must be nonzero")
        return value

    @model_validator(mode="after")
    def supported_asset_type(self) -> "StrategyDraftLeg":
        if self.asset_type not in {AssetType.EQUITY, AssetType.ETF, AssetType.OPTION}:
            raise ValueError("strategy drafts support equity, ETF, or option legs")
        return self


class StrategyDraftDefinition(DomainModel):
    name: str = Field(min_length=1, max_length=80)
    underlying_symbol: str = Field(min_length=1, max_length=12)
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    strategy_template_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    legs: tuple[StrategyDraftLeg, ...] = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized or not normalized.isprintable():
            raise ValueError("strategy draft name must be printable")
        return normalized

    @field_validator("underlying_symbol")
    @classmethod
    def normalize_underlying(cls, value: str) -> str:
        return normalize_watchlist_symbol(value)


class StrategyDraft(StrategyDraftDefinition):
    draft_id: UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)
