"""Shared strict model behavior for public domain contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, JsonValue


class DomainModel(BaseModel):
    """Base class that rejects unknown fields and supports immutable results."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


def require_aware_datetime(value: datetime) -> datetime:
    """Reject ambiguous provider timestamps at the domain boundary."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


def validate_provider_extensions(value: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Require extension keys to be namespaced, for example ``schwab.field``."""

    invalid = sorted(key for key in value if "." not in key)
    if invalid:
        raise ValueError(f"provider extension keys must be namespaced: {invalid}")
    return value
