"""Canonical quote, chain, provenance, and history models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import Field, JsonValue, field_validator, model_validator

from options_analysis.domain._base import (
    DomainModel,
    require_aware_datetime,
    validate_provider_extensions,
)
from options_analysis.domain.instruments import Instrument


class ProvenanceKind(StrEnum):
    PROVIDER = "provider"
    LOCAL_CALCULATION = "local_calculation"
    USER_INPUT = "user_input"


class FieldProvenance(DomainModel):
    kind: ProvenanceKind
    provider_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]*$")
    as_of: datetime
    method: str | None = None

    @field_validator("as_of")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def provider_is_present_for_provider_data(self) -> Self:
        if self.kind is ProvenanceKind.PROVIDER and self.provider_id is None:
            raise ValueError("provider_id is required for provider provenance")
        return self


class DataQualityWarning(DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    fields: tuple[str, ...] = ()


class OptionGreeks(DomainModel):
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None


class Quote(DomainModel):
    instrument: Instrument
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    as_of: datetime
    received_at: datetime
    bid: Decimal | None = Field(default=None, ge=Decimal("0"))
    ask: Decimal | None = Field(default=None, ge=Decimal("0"))
    bid_size: int | None = Field(default=None, ge=0)
    ask_size: int | None = Field(default=None, ge=0)
    last: Decimal | None = Field(default=None, ge=Decimal("0"))
    last_size: int | None = Field(default=None, ge=0)
    mark: Decimal | None = Field(default=None, ge=Decimal("0"))
    underlying_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, ge=0)
    implied_volatility: Decimal | None = Field(default=None, ge=Decimal("0"))
    greeks: OptionGreeks | None = None
    theoretical_value: Decimal | None = Field(default=None, ge=Decimal("0"))
    exchange: str | None = None
    security_status: str | None = None
    field_provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    provider_extensions: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: tuple[DataQualityWarning, ...] = ()

    @field_validator("as_of", "received_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @field_validator("provider_extensions")
    @classmethod
    def extensions_are_namespaced(
        cls, value: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        return validate_provider_extensions(value)

    @model_validator(mode="after")
    def provider_matches_instrument(self) -> Self:
        if self.provider_id != self.instrument.provider_id:
            raise ValueError("quote provider must match instrument provider")
        return self


class OptionChain(DomainModel):
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    underlying_symbol: str = Field(min_length=1)
    as_of: datetime
    underlying_quote: Quote | None = None
    contracts: tuple[Quote, ...]
    warnings: tuple[DataQualityWarning, ...] = ()

    @field_validator("underlying_symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("as_of")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def child_quotes_match_provider(self) -> Self:
        quotes = self.contracts
        if self.underlying_quote is not None:
            quotes = (self.underlying_quote, *quotes)
        if any(quote.provider_id != self.provider_id for quote in quotes):
            raise ValueError("all chain quotes must match the chain provider")
        return self


class PriceBar(DomainModel):
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    instrument: Instrument
    start: datetime
    end: datetime
    open: Decimal = Field(ge=Decimal("0"))
    high: Decimal = Field(ge=Decimal("0"))
    low: Decimal = Field(ge=Decimal("0"))
    close: Decimal = Field(ge=Decimal("0"))
    volume: int | None = Field(default=None, ge=0)

    @field_validator("start", "end")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def validate_bar(self) -> Self:
        if self.provider_id != self.instrument.provider_id:
            raise ValueError("bar provider must match instrument provider")
        if self.end <= self.start:
            raise ValueError("bar end must be after start")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("bar high is inconsistent with OHLC values")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("bar low is inconsistent with OHLC values")
        return self
