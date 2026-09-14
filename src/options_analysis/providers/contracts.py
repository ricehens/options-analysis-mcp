"""Small capability contracts implemented by data-source adapters."""

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, Self, runtime_checkable

from pydantic import Field, field_validator, model_validator

from options_analysis.domain import OptionChain, PositionLeg, PriceBar, PutCall, Quote
from options_analysis.domain._base import DomainModel, require_aware_datetime


class Capability(StrEnum):
    UNDERLYING_QUOTES = "underlying_quotes"
    OPTION_EXPIRATIONS = "option_expirations"
    OPTION_CHAINS = "option_chains"
    OPTION_QUOTES = "option_quotes"
    PROVIDER_GREEKS = "provider_greeks"
    OPEN_INTEREST = "open_interest"
    PRICE_HISTORY = "price_history"
    OPTION_HISTORY = "option_history"
    ACCOUNT_POSITIONS = "account_positions"
    STREAMING = "streaming"


class AuthenticationType(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    SESSION = "session"


class FreshnessMode(StrEnum):
    DETERMINISTIC = "deterministic"
    DELAYED = "delayed"
    REALTIME = "realtime"
    HISTORICAL = "historical"


class ProviderDescriptor(DomainModel):
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    display_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    authentication_type: AuthenticationType
    capabilities: frozenset[Capability]
    freshness_modes: frozenset[FreshnessMode]


class ProviderStatus(DomainModel):
    descriptor: ProviderDescriptor
    configured: bool
    ready: bool
    message: str | None = None


class OptionChainQuery(DomainModel):
    underlying_symbol: str = Field(min_length=1)
    expiration_from: date | None = None
    expiration_to: date | None = None
    put_call: PutCall | None = None
    strike_from: Decimal | None = Field(default=None, gt=Decimal("0"))
    strike_to: Decimal | None = Field(default=None, gt=Decimal("0"))
    limit: int = Field(default=100, ge=1, le=1_000)

    @field_validator("underlying_symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def ranges_are_ordered(self) -> Self:
        if (
            self.expiration_from is not None
            and self.expiration_to is not None
            and self.expiration_to < self.expiration_from
        ):
            raise ValueError("expiration_to must not precede expiration_from")
        if (
            self.strike_from is not None
            and self.strike_to is not None
            and self.strike_to < self.strike_from
        ):
            raise ValueError("strike_to must not be less than strike_from")
        return self


class PriceHistoryQuery(DomainModel):
    symbol: str = Field(min_length=1)
    start: datetime
    end: datetime
    resolution: str = Field(default="1d", min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("start", "end")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def time_range_is_ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("history end must be after start")
        return self


@runtime_checkable
class Provider(Protocol):
    @property
    def descriptor(self) -> ProviderDescriptor: ...

    def status(self) -> ProviderStatus: ...


@runtime_checkable
class MarketDataProvider(Provider, Protocol):
    async def get_underlying_quote(self, symbol: str) -> Quote: ...

    async def get_option_expirations(
        self, underlying_symbol: str
    ) -> tuple[date, ...]: ...

    async def get_option_chain(self, query: OptionChainQuery) -> OptionChain: ...

    async def get_option_quotes(
        self, symbols: tuple[str, ...]
    ) -> tuple[Quote, ...]: ...


@runtime_checkable
class HistoricalDataProvider(Provider, Protocol):
    async def get_price_history(
        self, query: PriceHistoryQuery
    ) -> tuple[PriceBar, ...]: ...


@runtime_checkable
class PortfolioProvider(Provider, Protocol):
    async def get_positions(
        self, account_id: str | None = None
    ) -> tuple[PositionLeg, ...]: ...


@runtime_checkable
class StreamingProvider(Provider, Protocol):
    def stream_quotes(self, symbols: tuple[str, ...]) -> AsyncIterator[Quote]: ...
