from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from options_analysis.domain import (
    AssetType,
    Instrument,
    LongShort,
    OptionTerms,
    PositionLeg,
    PutCall,
    Quote,
)

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def option_instrument(provider_id: str = "fake") -> Instrument:
    return Instrument(
        asset_type=AssetType.OPTION,
        symbol="AAPL300118C00100000",
        provider_id=provider_id,
        provider_symbol="AAPL300118C00100000",
        occ_symbol="AAPL300118C00100000",
        option=OptionTerms(
            underlying_symbol="aapl",
            expiration_date=date(2030, 1, 18),
            put_call=PutCall.CALL,
            strike=Decimal("100"),
        ),
    )


def test_option_instrument_requires_terms() -> None:
    with pytest.raises(ValidationError, match="option terms are required"):
        Instrument(
            asset_type=AssetType.OPTION,
            symbol="AAPL300118C00100000",
            provider_id="fake",
            provider_symbol="AAPL300118C00100000",
        )


def test_quote_rejects_mismatched_provider() -> None:
    with pytest.raises(ValidationError, match="quote provider must match"):
        Quote(
            instrument=option_instrument("fake"),
            provider_id="other",
            as_of=NOW,
            received_at=NOW,
        )


def test_quote_rejects_naive_timestamp_and_unnamespaced_extensions() -> None:
    instrument = option_instrument()
    with pytest.raises(ValidationError, match="timezone"):
        Quote(
            instrument=instrument,
            provider_id="fake",
            as_of=datetime(2026, 1, 2),
            received_at=NOW,
        )
    with pytest.raises(ValidationError, match="namespaced"):
        Quote(
            instrument=instrument,
            provider_id="fake",
            as_of=NOW,
            received_at=NOW,
            provider_extensions={"rawField": "value"},
        )


def test_position_direction_is_derived_from_signed_quantity() -> None:
    instrument = option_instrument()
    long_leg = PositionLeg(
        instrument=instrument,
        quantity=Decimal("2"),
        source="user",
        as_of=NOW,
    )
    short_leg = PositionLeg(
        instrument=instrument,
        quantity=Decimal("-1"),
        source="user",
        as_of=NOW,
    )

    assert long_leg.long_or_short is LongShort.LONG
    assert short_leg.long_or_short is LongShort.SHORT


def test_position_quantity_cannot_be_zero() -> None:
    with pytest.raises(ValidationError, match="quantity must be nonzero"):
        PositionLeg(
            instrument=option_instrument(),
            quantity=Decimal("0"),
            source="user",
            as_of=NOW,
        )
