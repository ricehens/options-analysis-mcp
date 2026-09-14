"""Provider-neutral market-data quality checks."""

from datetime import timedelta
from decimal import Decimal

from options_analysis.domain import DataQualityWarning


def quote_quality_warnings(
    *,
    bid: Decimal | None,
    ask: Decimal | None,
    mark: Decimal | None,
    age: timedelta,
    is_option: bool,
    open_interest: int | None = None,
    implied_volatility: Decimal | None = None,
    has_greeks: bool = False,
    timestamp_missing: bool = False,
    stale_after: timedelta = timedelta(minutes=15),
) -> tuple[DataQualityWarning, ...]:
    warnings: list[DataQualityWarning] = []
    if timestamp_missing:
        warnings.append(
            DataQualityWarning(
                code="missing_timestamp",
                message="Provider quote timestamp is missing; receipt time was used.",
                fields=("as_of",),
            )
        )
    elif age > stale_after:
        warnings.append(
            DataQualityWarning(
                code="stale_quote",
                message="Provider quote is older than the configured freshness window.",
                fields=("as_of",),
            )
        )
    if bid is None and ask is None:
        warnings.append(
            DataQualityWarning(
                code="missing_market",
                message="Both bid and ask are unavailable.",
                fields=("bid", "ask"),
            )
        )
    if bid is not None and ask is not None:
        if bid > ask:
            warnings.append(
                DataQualityWarning(
                    code="crossed_market",
                    message="Bid exceeds ask.",
                    fields=("bid", "ask"),
                )
            )
        if mark is not None and not bid <= mark <= ask:
            warnings.append(
                DataQualityWarning(
                    code="mark_outside_market",
                    message="Mark is outside the bid/ask market.",
                    fields=("bid", "ask", "mark"),
                )
            )
    if is_option:
        if open_interest is None:
            warnings.append(
                DataQualityWarning(
                    code="missing_open_interest",
                    message="Option open interest is unavailable.",
                    fields=("open_interest",),
                )
            )
        if implied_volatility is None:
            warnings.append(
                DataQualityWarning(
                    code="missing_implied_volatility",
                    message="Option implied volatility is unavailable.",
                    fields=("implied_volatility",),
                )
            )
        if not has_greeks:
            warnings.append(
                DataQualityWarning(
                    code="missing_greeks",
                    message="Provider option Greeks are unavailable.",
                    fields=("greeks",),
                )
            )
    return tuple(warnings)
