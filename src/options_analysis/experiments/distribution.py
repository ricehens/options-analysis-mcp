"""Conditional terminal payoff integration under explicit lognormal assumptions.

This experimental CLI deliberately lives on eshen/distribution-lab. It does
not infer real-world odds from option IV, option delta, or the pricing model.
"""

import argparse
import json
from datetime import date
from decimal import Decimal, localcontext
from html import escape
from math import erfc, exp, inf, log, sqrt
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from options_analysis.domain._base import DomainModel
from options_analysis.domain.research import ManualPositionLeg, ManualResearchRequest


class DistributionAssumption(DomainModel):
    name: str = Field(min_length=1, max_length=80)
    measure: Literal["subjective", "risk_neutral"]
    annual_drift: float = Field(ge=-1, le=1, allow_inf_nan=False)
    annual_volatility: float = Field(ge=0, le=5, allow_inf_nan=False)

    @field_validator("annual_volatility")
    @classmethod
    def supported_positive_volatility(cls, value: float) -> float:
        if 0 < value < 0.000001:
            raise ValueError("volatility must be zero or at least 0.000001")
        return value


class DistributionLabRequest(DomainModel):
    position: ManualResearchRequest
    assumptions: tuple[DistributionAssumption, ...] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def one_expiration_and_declared_measure(self) -> Self:
        expirations = {leg.expiration for leg in self.position.legs if leg.expiration}
        if len(expirations) != 1:
            raise ValueError(
                "distribution lab requires options with one shared expiration"
            )
        names = [item.name for item in self.assumptions]
        if len(set(names)) != len(names):
            raise ValueError("distribution assumption names must be unique")
        risk_neutral_drift = float(
            self.position.risk_free_rate - self.position.dividend_yield
        )
        for assumption in self.assumptions:
            if (
                assumption.measure == "risk_neutral"
                and abs(assumption.annual_drift - risk_neutral_drift) > 1e-10
            ):
                raise ValueError(
                    "risk-neutral price drift must equal the entered rate minus "
                    "dividend yield"
                )
        return self


class DistributionResult(DomainModel):
    assumption: DistributionAssumption
    probability_profit: float
    probability_loss: float
    probability_break_even: float
    integrated_probability: float
    expected_underlying_price: float
    expected_terminal_value: float
    expected_profit_loss: float
    deterministic_terminal_price: float | None


class DistributionLabResult(DomainModel):
    symbol: str
    valuation_date: date
    expiration_date: date
    days_to_expiration: int
    spot: float
    signed_entry_value: float
    reserved_fees: float
    results: tuple[DistributionResult, ...]
    limitations: tuple[str, ...]


def _units(leg: ManualPositionLeg) -> Decimal:
    assert leg.multiplier is not None
    return leg.quantity * leg.multiplier


def _value(legs: tuple[ManualPositionLeg, ...], spot: Decimal) -> Decimal:
    total = Decimal(0)
    for leg in legs:
        if leg.kind == "stock":
            value = spot
        else:
            assert leg.strike is not None
            value = max(
                Decimal(0),
                spot - leg.strike if leg.kind == "call" else leg.strike - spot,
            )
        total += value * _units(leg)
    return total


def _normal_interval(lower: float, upper: float) -> float:
    """Stable normal mass, avoiding cancellation in either far tail."""
    if lower >= upper:
        return 0
    if lower >= 0:
        return (erfc(lower / sqrt(2)) - erfc(upper / sqrt(2))) / 2
    return (erfc(-upper / sqrt(2)) - erfc(-lower / sqrt(2))) / 2


def _integrate(
    position: ManualResearchRequest,
    assumption: DistributionAssumption,
    days: int,
    basis: Decimal,
) -> DistributionResult:
    years = days / 365
    expected_spot = float(position.spot) * exp(assumption.annual_drift * years)
    deviation = assumption.annual_volatility * sqrt(years)
    if deviation == 0:
        terminal = _value(position.legs, Decimal(str(expected_spot)))
        profit = terminal - basis
        return DistributionResult(
            assumption=assumption,
            probability_profit=float(profit > 0),
            probability_loss=float(profit < 0),
            probability_break_even=float(profit == 0),
            integrated_probability=1,
            expected_underlying_price=expected_spot,
            expected_terminal_value=float(terminal),
            expected_profit_loss=float(profit),
            deterministic_terminal_price=expected_spot,
        )

    log_mean = (
        log(float(position.spot))
        + (assumption.annual_drift - assumption.annual_volatility**2 / 2) * years
    )

    def standard(price: Decimal | None) -> float:
        if price is None:
            return inf
        if price <= 0:
            return -inf
        return (log(float(price)) - log_mean) / deviation

    def mass(lower: Decimal, upper: Decimal | None) -> float:
        return _normal_interval(standard(lower), standard(upper))

    def first_moment(lower: Decimal, upper: Decimal | None) -> float:
        return expected_spot * _normal_interval(
            standard(lower) - deviation,
            standard(upper) - deviation,
        )

    knots = sorted(
        {Decimal(0), *(leg.strike for leg in position.legs if leg.strike is not None)}
    )
    profit_probability = loss_probability = zero_probability = total_mass = 0.0
    expected_profit = 0.0
    for index, lower in enumerate(knots):
        upper = knots[index + 1] if index + 1 < len(knots) else None
        slope = sum(
            (
                _units(leg)
                * (
                    1
                    if leg.kind == "stock"
                    or (
                        leg.kind == "call"
                        and leg.strike is not None
                        and leg.strike <= lower
                    )
                    else -1
                    if leg.kind == "put"
                    and leg.strike is not None
                    and leg.strike > lower
                    else 0
                )
                for leg in position.legs
            ),
            Decimal(0),
        )
        intercept = _value(position.legs, lower) - basis - slope * lower
        interval_mass = mass(lower, upper)
        total_mass += interval_mass
        expected_profit += (
            float(slope) * first_moment(lower, upper) + float(intercept) * interval_mass
        )
        if slope == 0:
            if intercept > 0:
                profit_probability += interval_mass
            elif intercept < 0:
                loss_probability += interval_mass
            else:
                zero_probability += interval_mass
            continue
        root = -intercept / slope
        split = max(lower, root)
        if upper is not None:
            split = min(split, upper)
        if slope > 0:
            profit_probability += mass(split, upper)
            loss_probability += mass(lower, split)
        else:
            profit_probability += mass(lower, split)
            loss_probability += mass(split, upper)

    if abs(total_mass - 1) > 1e-10:
        raise ValueError(
            "numeric integration did not normalize; assumptions unsupported"
        )
    # Correct only accumulated floating-point mass roundoff. Payoff and root
    # algebra above are Decimal; normal probabilities/first moments are floats.
    normalization = profit_probability + loss_probability + zero_probability
    return DistributionResult(
        assumption=assumption,
        probability_profit=profit_probability / normalization,
        probability_loss=loss_probability / normalization,
        probability_break_even=zero_probability / normalization,
        integrated_probability=total_mass,
        expected_underlying_price=expected_spot,
        expected_terminal_value=expected_profit + float(basis),
        expected_profit_loss=expected_profit,
        deterministic_terminal_price=None,
    )


def analyze_distribution(request: DistributionLabRequest) -> DistributionLabResult:
    """Integrate strict profitable/loss/flat regions and linear terminal values."""
    with localcontext() as context:
        context.prec = 128
        position = request.position
        expiration = next(leg.expiration for leg in position.legs if leg.expiration)
        days = (expiration - position.valuation_date).days
        entry = sum(
            (leg.entry_price * _units(leg) for leg in position.legs), Decimal(0)
        )
        fees = position.fixed_fees + 2 * position.fee_per_contract * sum(
            (abs(leg.quantity) for leg in position.legs if leg.kind != "stock"),
            Decimal(0),
        )
        return DistributionLabResult(
            symbol=position.symbol,
            valuation_date=position.valuation_date,
            expiration_date=expiration,
            days_to_expiration=days,
            spot=float(position.spot),
            signed_entry_value=float(entry),
            reserved_fees=float(fees),
            results=tuple(
                _integrate(position, assumption, days, entry + fees)
                for assumption in request.assumptions
            ),
            limitations=(
                "EXPERIMENT: conditional model probabilities, not a forecast, actual "
                "odds, a confidence interval or a trade recommendation.",
                "Underlying annual drift and volatility are explicitly supplied "
                "distribution assumptions. They are not inferred from option IV, "
                "delta or current marks.",
                "Risk-neutral probabilities are pricing-measure quantities, not "
                "real-world success rates. Subjective inputs are unverified beliefs; "
                "changing them changes every result.",
                "S(T)=S(0) exp((drift-volatility^2/2)T + volatility sqrt(T) Z), with "
                "Z standard normal and actual calendar days/365. Drift is expected "
                "PRICE growth, excluding cash dividends.",
                "Expected terminal P/L is undiscounted. Entry credits/costs and "
                "reserved round-trip fees count once. Expected value does not "
                "describe maximum loss, funding needs or typical outcomes.",
                "Probability of profit means strictly positive terminal P/L after "
                "fees. Flat zero-payoff regions count separately as break-even, not "
                "profit; deterministic cases retain any point mass.",
                "Standard share-deliverable contracts and one shared expiry only. No "
                "early exercise, assignment path, discrete dividends, slippage, "
                "taxes, borrow fees, margin or interim liquidation.",
                "A lognormal model excludes jumps, volatility changes, skew, tails "
                "beyond its assumptions and regime changes. Many leveraged ETFs "
                "reset daily: path-dependent compounding and volatility decay make "
                "a fixed "
                "terminal lognormal assumption especially fragile.",
                "Current marks, option IV, calibration, horizon controls and scenario"
                " IV shifts in the position input are not used here. Only spot, "
                "valuation/expiration dates, legs, entry prices, multipliers, rates "
                "for the risk-neutral-label check, and fees matter.",
                "Piecewise payoff regions are integrated analytically, including the "
                "infinite tail. Normal probabilities and truncated first moments use "
                "double precision; tiny mass normalization roundoff is corrected.",
            ),
        )


def render_report(
    request: DistributionLabRequest, result: DistributionLabResult
) -> str:
    """Standalone script-free, accessible report; all user content is escaped."""
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(value)}</td>"
            for value in (
                item.assumption.name,
                item.assumption.measure.replace("_", " "),
                f"{item.assumption.annual_drift:.1%}",
                f"{item.assumption.annual_volatility:.1%}",
                f"{item.probability_profit:.2%}",
                f"{item.probability_loss:.2%}",
                f"{item.probability_break_even:.2%}",
                f"${item.expected_profit_loss:,.2f}",
            )
        )
        + "</tr>"
        for item in result.results
    )
    leg_rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(str(value))}</td>"
            for value in (
                leg.kind,
                leg.quantity,
                leg.strike if leg.strike is not None else "-",
                leg.expiration or "-",
                leg.entry_price,
                leg.multiplier,
            )
        )
        + "</tr>"
        for leg in request.position.legs
    )
    notes = "".join(f"<li>{escape(note)}</li>" for note in result.limitations)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(result.symbol)} - distribution assumptions lab</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;
background:#f3f6f8;
color:#172a36;
margin:0}}main{{max-width:1150px;
margin:auto;
padding:32px 20px}}h1{{line-height:1.15}}.notice{{background:#fff1d6;
border-left:5px solid #986200;
padding:16px}}section{{background:white;
border:1px solid #d5dfe5;
border-radius:12px;
padding:22px;
margin:20px 0}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;
width:100%;
font-variant-numeric:tabular-nums}}th,td{{padding:12px;
text-align:left;
border-bottom:1px solid #d5dfe5;
white-space:nowrap}}th{{background:#e9f1f5}}caption{{text-align:left;
padding:0 0 12px;
font-weight:600}}li{{margin-bottom:12px}}small{{color:#40576a}}</style>
</head>
<body>
<main>
<p>
<strong>Isolated experiment · eshen/distribution-lab</strong>
</p>
<h1>How much do the assumptions matter?</h1>
<p class="notice">
<strong>Conditional probabilities are not forecasts.</strong> These results describe
only the declared terminal distributions. Risk-neutral probabilities are not real-world
trading odds.</p>
<section>
<h2>{escape(result.symbol)} · {result.valuation_date} to {result.expiration_date}</h2>
<p>Spot ${result.spot:,.2f} · {result.days_to_expiration} calendar days · signed entry
${result.signed_entry_value:,.2f} · reserved fees ${result.reserved_fees:,.2f}</p>
<div class="scroll" tabindex="0" aria-label="Declared distributions and conditional
outcomes">
<table>
<caption>Same position, separately declared distribution assumptions</caption>
<thead>
<tr>
<th scope="col">Assumption</th>
<th scope="col">Measure</th>
<th scope="col">Price drift</th>
<th scope="col">Volatility</th>
<th scope="col">P(profit)</th>
<th scope="col">P(loss)</th>
<th scope="col">P(flat zero)</th>
<th scope="col">Expected terminal P/L</th>
</tr>
</thead>
<tbody>{rows}</tbody>
</table>
</div>
<p>
<small>Profit means strictly positive terminal P/L after fees. Expected P/L is
undiscounted; no probability ranking or recommended trade is produced.</small>
</p>
</section>
<section>
<h2>Position accounting</h2>
<div class="scroll" tabindex="0" aria-label="Position legs">
<table>
<caption>Signed quantities; prices per underlying unit</caption>
<thead>
<tr>
<th scope="col">Kind</th>
<th scope="col">Quantity</th>
<th scope="col">Strike</th>
<th scope="col">Expiry</th>
<th scope="col">Entry/unit</th>
<th scope="col">Multiplier</th>
</tr>
</thead>
<tbody>{leg_rows}</tbody>
</table>
</div>
</section>
<section>
<h2>Assumptions and limitations</h2>
<ul>{notes}</ul>
</section>
</main>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experimental conditional distribution lab; not real-world odds."
    )
    parser.add_argument(
        "input", type=Path, help="JSON with position and explicit assumptions"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new output directory (never overwritten)",
    )
    arguments = parser.parse_args()
    try:
        if arguments.input.stat().st_size > 1_000_000:
            raise ValueError("input exceeds 1 MB")
        request = DistributionLabRequest.model_validate_json(
            arguments.input.read_text()
        )
        result = analyze_distribution(request)
        arguments.output_dir.mkdir(parents=True, exist_ok=False)
        (arguments.output_dir / "result.json").write_text(
            json.dumps(
                {
                    "input": request.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                },
                indent=2,
            )
            + "\n"
        )
        (arguments.output_dir / "report.html").write_text(
            render_report(request, result)
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Wrote {arguments.output_dir / 'report.html'} and result.json")


if __name__ == "__main__":
    main()
