"""Analytic identities for the isolated conditional probability experiment."""

from math import erf, exp, log, sqrt
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from options_analysis.experiments.distribution import (
    DistributionLabRequest,
    analyze_distribution,
    main,
    render_report,
)


def case(
    *legs: dict[str, Any],
    drift: float = 0.08,
    vol: float = 0.3,
    date: str = "2026-10-02",
    fees: float = 0,
    measure: str = "subjective",
) -> DistributionLabRequest:
    return DistributionLabRequest.model_validate(
        {
            "position": {
                "symbol": "XYZ",
                "spot": 100,
                "valuation_date": date,
                "legs": legs,
                "fixed_fees": fees,
                "risk_free_rate": 0.04,
            },
            "assumptions": [
                {
                    "name": "Explicit assumption",
                    "measure": measure,
                    "annual_drift": drift,
                    "annual_volatility": vol,
                }
            ],
        }
    )


def leg(
    kind: str = "call", qty: int = 1, strike: int = 100, entry: float = 5
) -> dict[str, Any]:
    return {
        "kind": kind,
        "quantity": qty,
        "strike": strike,
        "entry_price": entry,
        "expiration": "2027-10-02",
    }


def normal(value: float) -> float:
    return (1 + erf(value / sqrt(2))) / 2


@pytest.mark.parametrize("kind", ["call", "put"])
def test_vanilla_expected_payoff_and_profit_probability(kind: str) -> None:
    drift, vol, strike, premium = 0.08, 0.3, 100, 5
    result = analyze_distribution(case(leg(kind), drift=drift, vol=vol)).results[0]
    d1 = (drift + vol**2 / 2) / vol
    d2 = d1 - vol
    expected_call = 100 * exp(drift) * normal(d1) - strike * normal(d2)
    expected_payoff = (
        expected_call if kind == "call" else expected_call - 100 * exp(drift) + strike
    )
    threshold = strike + premium if kind == "call" else strike - premium
    z = (log(threshold / 100) - drift + vol**2 / 2) / vol
    probability = 1 - normal(z) if kind == "call" else normal(z)
    assert result.expected_profit_loss == pytest.approx(
        100 * (expected_payoff - premium), abs=1e-9
    )
    assert result.probability_profit == pytest.approx(probability, abs=1e-12)
    assert result.probability_break_even == 0


@pytest.mark.parametrize("strike", [60, 100, 140])
@pytest.mark.parametrize("vol", [0.05, 0.3, 5])
def test_long_short_complement_excludes_zero_plateau(strike: int, vol: float) -> None:
    long = analyze_distribution(case(leg(strike=strike, entry=0), vol=vol)).results[0]
    short = analyze_distribution(
        case(leg(qty=-1, strike=strike, entry=0), vol=vol)
    ).results[0]
    assert (
        long.probability_profit + short.probability_profit + long.probability_break_even
        == pytest.approx(1)
    )
    assert long.probability_break_even == pytest.approx(short.probability_break_even)
    assert long.expected_profit_loss == pytest.approx(-short.expected_profit_loss)
    assert long.probability_loss == 0
    assert short.probability_profit == 0


def test_strict_zero_profit_for_flat_offset_position() -> None:
    result = analyze_distribution(case(leg(), leg(qty=-1))).results[0]
    assert result.expected_profit_loss == 0
    assert result.probability_profit == 0
    assert result.probability_loss == 0
    assert result.probability_break_even == 1


def test_put_call_stock_parity_produces_constant_cash_payoff() -> None:
    stock = {"kind": "stock", "quantity": -100, "entry_price": 100}
    result = analyze_distribution(
        case(leg(entry=5), leg("put", qty=-1, entry=5), stock)
    ).results[0]
    assert result.expected_terminal_value == pytest.approx(-10000)
    assert result.expected_profit_loss == 0
    assert result.probability_break_even == 1


@pytest.mark.parametrize("drift", [-0.5, 0, 0.5])
def test_zero_volatility_deterministic_outcomes(drift: float) -> None:
    result = analyze_distribution(case(leg(), vol=0, drift=drift)).results[0]
    price = 100 * exp(drift)
    profit = 100 * max(price - 100, 0) - 500
    assert result.deterministic_terminal_price == pytest.approx(price)
    assert result.expected_profit_loss == pytest.approx(profit)
    assert result.probability_profit == float(profit > 0)
    assert result.probability_loss == float(profit < 0)


def test_zero_time_has_exact_expiry_intrinsic_despite_vol_and_drift() -> None:
    result = analyze_distribution(
        case(leg(strike=95, entry=5), date="2027-10-02", vol=5, drift=1)
    ).results[0]
    assert result.probability_break_even == 1
    assert result.expected_profit_loss == 0
    assert result.deterministic_terminal_price == 100


def test_credit_and_round_trip_fees_count_once() -> None:
    data = case(leg("put", qty=-1, strike=95, entry=2), vol=0, drift=0, fees=10)
    payload = data.model_dump(mode="json")
    payload["position"]["fee_per_contract"] = "0.65"
    result = analyze_distribution(DistributionLabRequest.model_validate(payload))
    assert result.signed_entry_value == -200
    assert result.reserved_fees == pytest.approx(11.3)
    assert result.results[0].expected_profit_loss == pytest.approx(188.7)
    assert result.results[0].probability_profit == 1


def test_declared_drift_and_volatility_change_outcomes() -> None:
    lower = analyze_distribution(case(leg(), drift=-0.1, vol=0.2)).results[0]
    higher = analyze_distribution(case(leg(), drift=0.1, vol=0.2)).results[0]
    wider = analyze_distribution(case(leg(), drift=0.1, vol=0.8)).results[0]
    assert higher.probability_profit > lower.probability_profit
    assert higher.expected_profit_loss > lower.expected_profit_loss
    assert wider.expected_profit_loss > higher.expected_profit_loss
    assert wider.probability_profit != higher.probability_profit


@pytest.mark.parametrize("vol", [0.000001, 0.1, 1, 5])
@pytest.mark.parametrize("drift", [-1, 0, 1])
def test_normalization_and_finite_very_wide_distribution(
    vol: float, drift: float
) -> None:
    data = case(
        leg("put", 1, 80, 1),
        leg("put", -1, 90, 3),
        leg("call", -1, 110, 3),
        leg("call", 1, 120, 1),
        vol=vol,
        drift=drift,
    )
    result = analyze_distribution(data).results[0]
    assert result.integrated_probability == pytest.approx(1, abs=1e-12)
    assert (
        result.probability_profit
        + result.probability_loss
        + result.probability_break_even
        == pytest.approx(1)
    )
    assert -600 <= result.expected_profit_loss <= 400


def test_option_iv_and_current_marks_do_not_supply_distribution_assumptions() -> None:
    baseline = case(leg())
    changed = baseline.model_dump(mode="json")
    changed["position"]["legs"][0]["implied_volatility"] = "4.0"
    changed["position"]["legs"][0]["current_price"] = "1000"
    assert analyze_distribution(baseline) == analyze_distribution(
        DistributionLabRequest.model_validate(changed)
    )


def test_invalid_or_ambiguous_measure_and_calendar_are_rejected() -> None:
    with pytest.raises(ValidationError, match="risk-neutral price drift"):
        case(leg(), drift=0.08, measure="risk_neutral")
    assert case(leg(), drift=0.04, measure="risk_neutral")
    with pytest.raises(ValidationError, match="shared expiration"):
        case(leg(), dict(leg(), expiration="2027-11-02"))
    with pytest.raises(ValidationError, match="shared expiration"):
        case({"kind": "stock", "quantity": 100, "entry_price": 100})
    with pytest.raises(ValidationError):
        case(leg(), vol=float("nan"))


def test_report_escapes_user_content_and_retains_accessible_table_structure() -> None:
    payload = case(leg()).model_dump(mode="json")
    payload["position"]["symbol"] = "<script>x</script>"
    payload["assumptions"][0]["name"] = '<img src=x onerror="alert(1)">'
    data = DistributionLabRequest.model_validate(payload)
    report = render_report(data, analyze_distribution(data))
    assert "<script>" not in report
    assert "<img " not in report
    assert "&lt;img" in report
    assert 'lang="en"' in report
    assert 'scope="col"' in report
    assert "<caption>" in report
    assert 'tabindex="0"' in report


def test_cli_outputs_json_and_html_without_overwriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "input.json"
    source.write_text(case(leg()).model_dump_json())
    output = tmp_path / "report"
    monkeypatch.setattr(
        "sys.argv", ["distribution-lab", str(source), "--output-dir", str(output)]
    )
    main()
    content = (output / "result.json").read_text()
    assert '"probability_profit"' in content
    assert '"annual_volatility"' in content
    assert (output / "report.html").read_text().startswith("<!doctype html>")
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert (output / "result.json").read_text() == content


def test_cli_rejects_oversized_input_before_creating_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "large.json"
    source.write_text(" " * 1_000_001)
    output = tmp_path / "report"
    monkeypatch.setattr(
        "sys.argv", ["distribution-lab", str(source), "--output-dir", str(output)]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not output.exists()
