"""Provider-neutral watchlist models."""

import re
from datetime import datetime

from pydantic import Field, field_validator

from options_analysis.domain._base import DomainModel, require_aware_datetime

_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,11}$")


def normalize_watchlist_symbol(value: str) -> str:
    normalized = value.strip().upper()
    if not _SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError(
            "symbol must start with a letter and contain at most 12 letters, "
            "numbers, dots, or hyphens"
        )
    return normalized


class WatchlistItem(DomainModel):
    symbol: str = Field(min_length=1, max_length=12)
    created_at: datetime
    sort_order: int = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return normalize_watchlist_symbol(value)

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)
