"""Provider-neutral option and underlying positions."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import Field, field_validator, model_validator

from options_analysis.domain._base import DomainModel, require_aware_datetime
from options_analysis.domain.instruments import Instrument
from options_analysis.domain.market_data import Quote


class LongShort(StrEnum):
    LONG = "long"
    SHORT = "short"


class PositionLeg(DomainModel):
    instrument: Instrument
    quantity: Decimal
    average_open_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    current_quote: Quote | None = None
    market_value: Decimal | None = None
    cost_basis: Decimal | None = None
    unrealized_profit_loss: Decimal | None = None
    source: str = Field(min_length=1)
    as_of: datetime

    @field_validator("quantity")
    @classmethod
    def quantity_is_nonzero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("position quantity must be nonzero")
        return value

    @field_validator("as_of")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def quote_matches_instrument(self) -> Self:
        if self.current_quote is None:
            return self
        quote_instrument = self.current_quote.instrument
        if (
            quote_instrument.provider_id != self.instrument.provider_id
            or quote_instrument.provider_symbol != self.instrument.provider_symbol
        ):
            raise ValueError("position quote must refer to the same instrument")
        return self

    @property
    def long_or_short(self) -> LongShort:
        return LongShort.LONG if self.quantity > 0 else LongShort.SHORT
