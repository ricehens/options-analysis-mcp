"""Versioned, provider-neutral local replay bundle schema."""

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from options_analysis.domain import OptionChain, PriceBar, Quote
from options_analysis.domain._base import DomainModel, require_aware_datetime


class ReplaySource(DomainModel):
    """Human-auditable origin and usage notes for a replay dataset."""

    label: str = Field(min_length=1, max_length=200)
    original_provider_id: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9_-]*$"
    )
    acquired_at: datetime
    usage_notes: str | None = Field(default=None, max_length=1_000)

    @field_validator("acquired_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class ReplayHistorySeries(DomainModel):
    resolution: str = Field(min_length=1, max_length=20)
    bars: tuple[PriceBar, ...] = Field(max_length=10_000)

    @field_validator("resolution")
    @classmethod
    def normalize_resolution(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def bars_are_ordered(self) -> Self:
        starts = tuple(bar.start for bar in self.bars)
        if starts != tuple(sorted(starts)):
            raise ValueError("replay history bars must be ordered oldest to newest")
        return self


class ReplaySymbolSnapshot(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    underlying_quote: Quote
    option_chain: OptionChain
    price_history: tuple[ReplayHistorySeries, ...] = Field(max_length=32)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def contents_match_symbol(self) -> Self:
        if self.underlying_quote.instrument.symbol != self.symbol:
            raise ValueError("replay underlying quote must match snapshot symbol")
        if self.option_chain.underlying_symbol != self.symbol:
            raise ValueError("replay option chain must match snapshot symbol")
        resolutions = tuple(series.resolution for series in self.price_history)
        if len(resolutions) != len(set(resolutions)):
            raise ValueError("replay history resolutions must be unique per symbol")
        for series in self.price_history:
            if any(bar.instrument.symbol != self.symbol for bar in series.bars):
                raise ValueError(
                    "replay history instruments must match snapshot symbol"
                )
        return self


class ReplayBundle(DomainModel):
    """Portable canonical snapshots; upstream-specific bodies are not required."""

    schema_version: Literal[1] = 1
    created_at: datetime
    source: ReplaySource
    symbols: tuple[ReplaySymbolSnapshot, ...] = Field(min_length=1, max_length=500)

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def symbols_and_contracts_are_unique(self) -> Self:
        symbols = tuple(item.symbol for item in self.symbols)
        if len(symbols) != len(set(symbols)):
            raise ValueError("replay bundle symbols must be unique")
        option_symbols = tuple(
            quote.instrument.provider_symbol.upper()
            for item in self.symbols
            for quote in item.option_chain.contracts
        )
        if len(option_symbols) != len(set(option_symbols)):
            raise ValueError("replay option provider symbols must be unique")
        return self
