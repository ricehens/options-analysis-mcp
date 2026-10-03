"""Compare hold, close, and explicit trades with one cash-flow ledger.

Trade quantities are buys positive and sells negative. They are changes to the
original position, not a replacement position. Execution assumptions are always
explicit and are never silently replaced with modeled prices.
"""

from datetime import date, timedelta
from decimal import Decimal, localcontext
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from options_analysis.analytics.pricing import european_option
from options_analysis.analytics.research import analyze_manual_position
from options_analysis.domain._base import DomainModel
from options_analysis.domain.research import (
    ManualPositionLeg,
    ManualResearchRequest,
    ResearchDecimal,
    _bounded_precision,
)

ZERO = Decimal(0)
ContractKey = tuple[str, Decimal | None, date | None, Decimal]


class _LabInputModel(DomainModel):
    @field_validator("*")
    @classmethod
    def bounded_numeric_precision(cls, value: object) -> object:
        return _bounded_precision(value) if isinstance(value, Decimal) else value


class AdjustmentTrade(_LabInputModel):
    kind: Literal["stock", "call", "put"]
    quantity: ResearchDecimal = Field(ge=-1000000, le=1000000)
    fill_price: ResearchDecimal = Field(ge=0, le=1000000)
    fees: ResearchDecimal = Field(default=ZERO, ge=0, le=1000000)
    strike: ResearchDecimal | None = None
    expiration: date | None = None
    multiplier: ResearchDecimal | None = None
    implied_volatility: ResearchDecimal | None = Field(default=None, ge=0, le=5)

    def as_leg(self, iv: Decimal = Decimal("0.30")) -> ManualPositionLeg:
        return ManualPositionLeg(
            kind=self.kind,
            quantity=self.quantity,
            entry_price=self.fill_price,
            strike=self.strike,
            expiration=self.expiration,
            multiplier=self.multiplier,
            implied_volatility=self.implied_volatility
            if self.implied_volatility is not None
            else iv,
        )

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        self.as_leg()
        return self


class AdjustmentPlan(_LabInputModel):
    name: str = Field(min_length=1, max_length=80)
    trades: tuple[AdjustmentTrade, ...] = Field(min_length=1, max_length=40)
    future_exit_fees: ResearchDecimal = Field(default=ZERO, ge=0, le=1000000)


class CloseFill(_LabInputModel):
    leg_index: int = Field(ge=0, le=39)
    fill_price: ResearchDecimal = Field(ge=0, le=1000000)
    fees: ResearchDecimal = Field(default=ZERO, ge=0, le=1000000)


class AdjustmentComparisonRequest(_LabInputModel):
    position: ManualResearchRequest
    entry_fees: ResearchDecimal = Field(default=ZERO, ge=0, le=1000000)
    hold_future_exit_fees: ResearchDecimal = Field(default=ZERO, ge=0, le=1000000)
    close_fills: tuple[CloseFill, ...] = Field(min_length=1, max_length=40)
    adjustments: tuple[AdjustmentPlan, ...] = Field(default=(), max_length=8)

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if self.position.fee_per_contract or self.position.fixed_fees:
            raise ValueError(
                "Set position fee_per_contract and fixed_fees to zero. This lab "
                "uses actual entry_fees, trade fees, and explicit future_exit_fees."
            )
        indices = [fill.leg_index for fill in self.close_fills]
        if sorted(indices) != list(range(len(self.position.legs))):
            raise ValueError(
                "close_fills must contain each original leg_index exactly once"
            )
        names = [plan.name.casefold() for plan in self.adjustments]
        if len(set(names)) != len(names) or {"hold", "close"}.intersection(names):
            raise ValueError(
                "adjustment names must be unique and cannot be Hold or Close"
            )
        if self.position.horizon_days > (date.max - self.position.valuation_date).days:
            raise ValueError("common horizon exceeds the supported calendar")
        horizon = self.position.valuation_date + timedelta(
            days=self.position.horizon_days
        )
        legs = list(self.position.legs)
        legs.extend(
            trade.as_leg() for plan in self.adjustments for trade in plan.trades
        )
        for leg in legs:
            if leg.expiration is not None:
                if leg.expiration < horizon:
                    raise ValueError(
                        "The common horizon cannot follow any original or traded "
                        "option expiration; choose an earlier horizon."
                    )
                if (leg.expiration - self.position.valuation_date).days > 3650:
                    raise ValueError("traded option expiration must be within 10 years")
        return self


class ComparisonPoint(DomainModel):
    underlying_price: ResearchDecimal
    future_position_value: ResearchDecimal
    wealth: ResearchDecimal
    total_profit_loss: ResearchDecimal
    change_from_today: ResearchDecimal
    advantage_vs_hold: ResearchDecimal


class CashFlow(DomainModel):
    contract: str
    quantity_change: ResearchDecimal
    multiplier: ResearchDecimal
    fill_price: ResearchDecimal
    gross_cash_flow: ResearchDecimal
    fees: ResearchDecimal
    net_cash_flow: ResearchDecimal


class ComparisonAlternative(DomainModel):
    name: str
    remaining_legs: tuple[ManualPositionLeg, ...]
    cash_flows: tuple[CashFlow, ...]
    gross_cash_flow: ResearchDecimal
    transaction_fees: ResearchDecimal
    net_cash_flow: ResearchDecimal
    future_exit_fees: ResearchDecimal
    scenarios: tuple[ComparisonPoint, ...]
    curve: tuple[ComparisonPoint, ...]


class AdjustmentComparison(DomainModel):
    symbol: str
    valuation_date: date
    horizon_date: date
    spot: ResearchDecimal
    entry_value: ResearchDecimal
    entry_fees: ResearchDecimal
    current_position_value: ResearchDecimal
    current_profit_loss: ResearchDecimal
    alternatives: tuple[ComparisonAlternative, ...]
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]


def _key(leg: ManualPositionLeg) -> ContractKey:
    assert leg.multiplier is not None
    return leg.kind, leg.strike, leg.expiration, leg.multiplier


def _units(leg: ManualPositionLeg) -> Decimal:
    assert leg.multiplier is not None
    return leg.quantity * leg.multiplier


def _label(leg: ManualPositionLeg) -> str:
    if leg.kind == "stock":
        return "Stock shares"
    return f"{leg.expiration} {leg.strike} {leg.kind}, multiplier {leg.multiplier}"


def _flow(leg: ManualPositionLeg, price: Decimal, fees: Decimal) -> CashFlow:
    assert leg.multiplier is not None
    cash = -_units(leg) * price
    return CashFlow(
        contract=_label(leg),
        quantity_change=leg.quantity,
        multiplier=leg.multiplier,
        fill_price=price,
        gross_cash_flow=cash,
        fees=fees,
        net_cash_flow=cash - fees,
    )


def _value(
    legs: tuple[ManualPositionLeg, ...],
    source: ManualResearchRequest,
    spot: Decimal,
) -> Decimal:
    total = ZERO
    for leg in legs:
        if leg.kind == "stock":
            price = spot
        else:
            assert leg.expiration is not None and leg.strike is not None
            remaining = (
                leg.expiration - source.valuation_date
            ).days - source.horizon_days
            if remaining == 0:
                price = max(
                    spot - leg.strike if leg.kind == "call" else leg.strike - spot,
                    ZERO,
                )
            else:
                estimate = european_option(
                    leg.kind,
                    float(spot),
                    float(leg.strike),
                    remaining / 365,
                    float(leg.implied_volatility + source.iv_shift),
                    float(source.risk_free_rate),
                    float(source.dividend_yield),
                )
                price = Decimal(str(estimate.price))
        total += price * _units(leg)
    return total


def compare_adjustments(request: AdjustmentComparisonRequest) -> AdjustmentComparison:
    """Keep ledger products and cancellation exact beyond input precision.

    Three bounded 32-digit quantities can multiply in a cash-flow row, followed
    by at most 40 row additions. Use the same local precision as core research
    so small retained positions and cash differences survive cancellation.
    """
    with localcontext() as context:
        context.prec = 128
        return _compare_adjustments(request)


def _compare_adjustments(request: AdjustmentComparisonRequest) -> AdjustmentComparison:
    source = request.position
    original = analyze_manual_position(source)
    warnings = [f"{item.title}: {item.detail}" for item in original.findings]
    originals: dict[ContractKey, ManualPositionLeg] = {}
    for leg in original.legs:
        key = _key(leg)
        if key in originals:
            previous = originals[key]
            if (
                leg.kind != "stock"
                and previous.implied_volatility != leg.implied_volatility
            ):
                raise ValueError(
                    "identical original contracts must use the same effective IV"
                )
        else:
            originals[key] = leg

    # Keep lots separate for Hold. Adjustment netting removes zero positions and
    # ensures a bought-to-close contract inherits its original scenario IV.
    alternatives: list[
        tuple[str, tuple[ManualPositionLeg, ...], tuple[CashFlow, ...], Decimal]
    ] = [
        ("Hold", original.legs, (), request.hold_future_exit_fees),
    ]
    close_flows = tuple(
        _flow(
            original.legs[fill.leg_index].model_copy(
                update={"quantity": -original.legs[fill.leg_index].quantity}
            ),
            fill.fill_price,
            fill.fees,
        )
        for fill in sorted(request.close_fills, key=lambda item: item.leg_index)
    )
    alternatives.append(("Close", (), close_flows, ZERO))
    for plan in request.adjustments:
        contract_terms = dict(originals)
        quantities: dict[ContractKey, Decimal] = {}
        for leg in original.legs:
            key = _key(leg)
            quantities[key] = quantities.get(key, ZERO) + leg.quantity
        trade_flows: list[CashFlow] = []
        for trade in plan.trades:
            leg = trade.as_leg()
            key = _key(leg)
            if key in contract_terms:
                known_iv = contract_terms[key].implied_volatility
                if (
                    leg.kind != "stock"
                    and trade.implied_volatility is not None
                    and trade.implied_volatility != known_iv
                ):
                    raise ValueError(
                        f"{plan.name}: an existing contract must retain its "
                        "effective IV; "
                        "omit implied_volatility on its trade to inherit it"
                    )
                leg = leg.model_copy(update={"implied_volatility": known_iv})
            else:
                if leg.kind != "stock" and trade.implied_volatility is None:
                    raise ValueError(
                        f"{plan.name}: new option contracts require implied_volatility"
                    )
                contract_terms[key] = leg
            shifted = leg.implied_volatility + source.iv_shift
            if leg.kind != "stock" and (
                not 0 <= shifted <= 5 or 0 < shifted < Decimal("0.000001")
            ):
                raise ValueError(
                    f"{plan.name}: shifted IV must be zero or between 0.000001 and 5"
                )
            quantities[key] = quantities.get(key, ZERO) + leg.quantity
            trade_flows.append(_flow(leg, trade.fill_price, trade.fees))
        remaining = tuple(
            ManualPositionLeg.model_validate(
                {
                    **contract_terms[key].model_dump(),
                    "quantity": quantity,
                    "entry_price": ZERO,
                    "current_price": None,
                }
            )
            for key, quantity in quantities.items()
            if quantity
        )
        if not remaining and plan.future_exit_fees:
            raise ValueError(
                f"{plan.name}: an empty position cannot reserve future exit fees"
            )
        alternatives.append(
            (plan.name, remaining, tuple(trade_flows), plan.future_exit_fees)
        )

    scenario_prices = tuple(source.spot * (1 + move) for move in source.scenario_moves)
    strikes = [
        leg.strike
        for _, legs, _, _ in alternatives
        for leg in legs
        if leg.strike is not None
    ]
    low = min(source.spot * Decimal("0.7"), *scenario_prices, *strikes)
    high = max(source.spot * Decimal("1.3"), *scenario_prices, *strikes)
    curve_prices = tuple(
        sorted(
            {low + (high - low) * Decimal(i) / 100 for i in range(101)}
            | {source.spot, *strikes, *scenario_prices}
        )
    )
    hold_values = {
        price: _value(original.legs, source, price) - request.hold_future_exit_fees
        for price in {*curve_prices, *scenario_prices}
    }
    results: list[ComparisonAlternative] = []
    for name, legs, flows, future_fees in alternatives:
        gross = sum((flow.gross_cash_flow for flow in flows), ZERO)
        fees = sum((flow.fees for flow in flows), ZERO)
        cash = gross - fees

        def point(
            price: Decimal,
            legs: tuple[ManualPositionLeg, ...] = legs,
            cash: Decimal = cash,
            future_fees: Decimal = future_fees,
        ) -> ComparisonPoint:
            value = _value(legs, source, price)
            wealth = cash + value - future_fees
            return ComparisonPoint(
                underlying_price=price,
                future_position_value=value,
                wealth=wealth,
                total_profit_loss=wealth
                - original.net_entry_value
                - request.entry_fees,
                change_from_today=wealth - original.current_value,
                advantage_vs_hold=wealth - hold_values[price],
            )

        results.append(
            ComparisonAlternative(
                name=name,
                remaining_legs=legs,
                cash_flows=flows,
                gross_cash_flow=gross,
                transaction_fees=fees,
                net_cash_flow=cash,
                future_exit_fees=future_fees,
                scenarios=tuple(point(price) for price in scenario_prices),
                curve=tuple(point(price) for price in curve_prices),
            )
        )
    return AdjustmentComparison(
        symbol=source.symbol,
        valuation_date=source.valuation_date,
        horizon_date=source.valuation_date + timedelta(days=source.horizon_days),
        spot=source.spot,
        entry_value=original.net_entry_value,
        entry_fees=request.entry_fees,
        current_position_value=original.current_value,
        current_profit_loss=original.current_value
        - original.net_entry_value
        - request.entry_fees,
        alternatives=tuple(results),
        warnings=tuple(warnings),
        assumptions=(
            "All alternatives act today and share the same future date, underlying "
            "prices, rates, dividend yield, and absolute IV shift. No alternative "
            "is recommended.",
            "A positive trade quantity buys; a negative quantity sells. Gross cash "
            "flow is minus quantity times multiplier times fill price. Net cash "
            "subtracts transaction fees.",
            "Future wealth = today's net trade cash + future signed position value "
            "- reserved future exit fees. Positive wealth includes cash and assets; "
            "negative wealth includes liabilities.",
            "Total P/L = future wealth - original signed entry value - actual entry "
            "fees. Change from today = future wealth - today's entered/model "
            "position value. Original basis is never reset during a roll.",
            "Advantage vs Hold compares future wealth after each alternative's "
            "specified fees. It is a scenario difference, not a predicted return "
            "or probability.",
            "Fill prices are explicit user assumptions, not executable quotes. "
            "A Close result stays flat; cash earns no interest and negative cash "
            "has no financing charge.",
            "Future options use the European model until expiry and exact "
            "intrinsic value at expiry. Current marks may differ from modeled "
            "values, including in a zero-day scenario.",
            "Known contracts inherit effective original IV; new option contracts "
            "require an explicit IV. Stock dividends, early exercise, assignment, "
            "borrow costs, margin and taxes are excluded.",
            "Fees use this lab's actual-entry, trade, and future-exit fields. "
            "Core research round-trip fee reserves must be zero to avoid "
            "double counting.",
            "The common horizon may not follow any original or traded option "
            "expiry. Only standard contract deliverables are supported. The finite "
            "curve is not a maximum-loss guarantee.",
            "Cash-flow rows are economic receipts and payments, not tax-lot "
            "realized gains. This report does not model tax deferral, wash sales "
            "or lot selection.",
            "The lab uses position.horizon_days for its one common future date; "
            "position.scenario_days and risk_budget do not affect this comparison.",
        ),
    )
