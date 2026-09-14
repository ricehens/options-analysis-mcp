"""Provider-neutral instrument identity."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import Field, field_validator, model_validator

from options_analysis.domain._base import DomainModel, require_aware_datetime


class AssetType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    OPTION = "option"


class PutCall(StrEnum):
    PUT = "put"
    CALL = "call"


class ExerciseStyle(StrEnum):
    AMERICAN = "american"
    EUROPEAN = "european"


class SettlementType(StrEnum):
    PHYSICAL = "physical"
    CASH = "cash"


class OptionTerms(DomainModel):
    underlying_symbol: str = Field(min_length=1)
    option_root: str | None = None
    expiration_date: date
    last_trading_datetime: datetime | None = None
    put_call: PutCall
    strike: Decimal = Field(gt=Decimal("0"))
    multiplier: Decimal = Field(default=Decimal("100"), gt=Decimal("0"))
    deliverables: tuple[str, ...] = ()
    exercise_style: ExerciseStyle | None = None
    settlement_type: SettlementType | None = None
    is_adjusted: bool | None = None

    @field_validator("underlying_symbol", "option_root")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @field_validator("last_trading_datetime")
    @classmethod
    def timestamp_is_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_aware_datetime(value)


class Instrument(DomainModel):
    asset_type: AssetType
    symbol: str = Field(min_length=1)
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    provider_symbol: str = Field(min_length=1)
    occ_symbol: str | None = None
    option: OptionTerms | None = None

    @field_validator("symbol", "occ_symbol")
    @classmethod
    def normalize_canonical_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @model_validator(mode="after")
    def option_fields_match_asset_type(self) -> Self:
        if self.asset_type is AssetType.OPTION and self.option is None:
            raise ValueError("option terms are required for an option instrument")
        if self.asset_type is not AssetType.OPTION and self.option is not None:
            raise ValueError("option terms are only valid for an option instrument")
        return self
