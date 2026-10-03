from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from options_analysis.experiments.adjustment_report import render_adjustment_report
from options_analysis.experiments.adjustments import (
    AdjustmentComparisonRequest,
    compare_adjustments,
)


def sample() -> dict:
    path = Path(__file__).parents[2] / "examples" / "adjustment-comparison.json"
    import json

    return json.loads(path.read_text())


def without_fees() -> dict:
    data = sample()
    data["entry_fees"] = 0
    data["hold_future_exit_fees"] = 0
    for fill in data["close_fills"]:
        fill["fees"] = 0
    for plan in data["adjustments"]:
        plan["future_exit_fees"] = 0
        for trade in plan["trades"]:
            trade["fees"] = 0
    return data


def test_roll_preserves_original_basis_and_both_closing_and_opening_cash() -> None:
    result = compare_adjustments(
        AdjustmentComparisonRequest.model_validate(without_fees())
    )
    hold, close, pair, short_only = result.alternatives
    assert result.entry_value == 400
    assert result.current_position_value == 300
    assert result.current_profit_loss == -100
    assert pair.net_cash_flow == -240  # -910 + 290 + 490 - 110
    assert len(pair.cash_flows) == 4
    assert [(leg.strike, leg.quantity) for leg in pair.remaining_legs] == [
        (Decimal(100), Decimal(1)),
        (Decimal(120), Decimal(-1)),
        (Decimal(130), Decimal(-1)),
        (Decimal(150), Decimal(1)),
    ]
    at130 = next(point for point in pair.scenarios if point.underlying_price == 130)
    assert at130.future_position_value == 2000
    assert at130.wealth == 1760
    assert at130.total_profit_loss == 1360
    assert at130.change_from_today == 1460
    assert at130.advantage_vs_hold == 760
    assert all(point.advantage_vs_hold == 0 for point in hold.scenarios)
    assert len({point.total_profit_loss for point in close.scenarios}) == 1
    assert close.net_cash_flow == 260  # 1790 - 1820 + 290
    assert close.scenarios[0].total_profit_loss == -140
    assert close.scenarios[0].change_from_today == -40
    assert short_only.net_cash_flow == -420
    assert pair.scenarios[-1].total_profit_loss == -640


def test_actual_and_reserved_fees_are_each_counted_once() -> None:
    data = sample()
    result = compare_adjustments(AdjustmentComparisonRequest.model_validate(data))
    hold, close, pair, _ = result.alternatives
    assert result.current_profit_loss == Decimal("-102.6")
    assert close.transaction_fees == Decimal("2.6")
    assert close.net_cash_flow == Decimal("257.4")
    assert close.scenarios[0].total_profit_loss == Decimal("-145.2")
    assert pair.transaction_fees == Decimal("2.6")
    assert pair.net_cash_flow == Decimal("-242.6")
    assert pair.scenarios[3].wealth == Decimal("1754.8")
    assert pair.scenarios[3].total_profit_loss == Decimal("1352.2")
    assert hold.scenarios[3].wealth == Decimal("997.4")


def test_close_short_credit_position_counts_liability_and_credit_once() -> None:
    data = {
        "position": {
            "symbol": "DEMO",
            "spot": 100,
            "valuation_date": "2026-10-01",
            "horizon_days": 92,
            "scenario_moves": [0, 0.3],
            "legs": [
                {
                    "kind": "call",
                    "quantity": -1,
                    "strike": 120,
                    "expiration": "2027-01-01",
                    "entry_price": 5,
                    "current_price": 2,
                }
            ],
        },
        "close_fills": [{"leg_index": 0, "fill_price": 2.1}],
    }
    result = compare_adjustments(AdjustmentComparisonRequest.model_validate(data))
    hold, close = result.alternatives
    assert result.entry_value == -500
    assert result.current_position_value == -200
    assert close.net_cash_flow == -210
    assert close.scenarios[0].total_profit_loss == 290
    assert close.scenarios[0].change_from_today == -10
    assert hold.scenarios[1].total_profit_loss == -500


@pytest.mark.parametrize("problem", ["missing", "duplicate"])
def test_close_requires_one_explicit_fill_per_original_leg(problem: str) -> None:
    data = sample()
    if problem == "missing":
        data["close_fills"].pop()
    else:
        data["close_fills"][2]["leg_index"] = 0
    with pytest.raises(ValueError, match="each original leg_index exactly once"):
        AdjustmentComparisonRequest.model_validate(data)


def test_common_horizon_does_not_silently_cap_different_alternatives() -> None:
    data = sample()
    data["adjustments"][0]["trades"][2]["expiration"] = "2026-12-01"
    with pytest.raises(ValueError, match="common horizon cannot follow"):
        AdjustmentComparisonRequest.model_validate(data)


def test_new_contracts_need_iv_and_existing_contracts_share_iv() -> None:
    data = sample()
    del data["adjustments"][0]["trades"][2]["implied_volatility"]
    with pytest.raises(ValueError, match="new option contracts require"):
        compare_adjustments(AdjustmentComparisonRequest.model_validate(data))
    data = sample()
    data["adjustments"][0]["trades"][0]["implied_volatility"] = 0.9
    with pytest.raises(ValueError, match="retain its effective IV"):
        compare_adjustments(AdjustmentComparisonRequest.model_validate(data))


def test_main_research_round_trip_reserves_cannot_be_double_counted() -> None:
    data = sample()
    data["position"]["fee_per_contract"] = 0.65
    with pytest.raises(ValueError, match="actual entry_fees"):
        AdjustmentComparisonRequest.model_validate(data)


def test_report_escapes_html_script_and_template_placeholder_labels() -> None:
    data = sample()
    data["adjustments"][0]["name"] = "</script><img src=x onerror=alert(1)>__DATA__"
    result = compare_adjustments(AdjustmentComparisonRequest.model_validate(data))
    html = render_adjustment_report(result)
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html
    assert "\\u003c/script\\u003e" in html
    assert html.count('<script type="application/json"') == 1
    assert html.count("</script>") == 2
    assert "__DATA__" in html  # Literal user text must not become template content.


def test_zero_day_theoretical_mark_mismatch_is_not_hidden() -> None:
    data = sample()
    data["position"]["horizon_days"] = 0
    data["position"]["scenario_moves"] = [0]
    result = compare_adjustments(AdjustmentComparisonRequest.model_validate(data))
    assert result.alternatives[0].scenarios[0].change_from_today != 0
    assert any("Entered marks differ" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "path",
    [
        ("entry_fees",),
        ("hold_future_exit_fees",),
        ("close_fills", 0, "fill_price"),
        ("close_fills", 0, "fees"),
        ("adjustments", 0, "future_exit_fees"),
        ("adjustments", 0, "trades", 0, "fees"),
        ("adjustments", 0, "trades", 0, "fill_price"),
    ],
)
@pytest.mark.parametrize("value", ["0e-100000000", "0." + "1" * 33])
def test_lab_numeric_imports_bound_output_size(path: tuple, value: str) -> None:
    data = sample()
    target = data
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(ValueError, match=r"at most (30 decimal places|32 significant)"):
        AdjustmentComparisonRequest.model_validate(data)


def test_small_cash_difference_survives_large_close_flows_and_caller_precision() -> (
    None
):
    # Each fill is within the precision limit, but multiplying and then netting
    # these two stock trades needs more than Decimal's default 28 digits.
    data = {
        "position": {
            "symbol": "DEMO",
            "spot": 1,
            "valuation_date": "2026-10-01",
            "horizon_days": 1,
            "scenario_moves": [0],
            "legs": [
                {"kind": "stock", "quantity": 1000000, "entry_price": 1},
                {"kind": "stock", "quantity": -1000000, "entry_price": 1},
            ],
        },
        "close_fills": [
            {"leg_index": 0, "fill_price": "1.000000000000000000000000000001"},
            {"leg_index": 1, "fill_price": "1"},
        ],
    }
    request = AdjustmentComparisonRequest.model_validate(data)
    with localcontext() as context:
        context.prec = 12
        result = compare_adjustments(request)
        assert context.prec == 12
    assert result.alternatives[1].net_cash_flow == Decimal("1e-24")
    assert result.alternatives[1].scenarios[0].total_profit_loss == Decimal("1e-24")
