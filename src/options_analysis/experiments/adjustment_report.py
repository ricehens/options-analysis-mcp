"""Escaped, self-contained HTML for the optional adjustment comparison lab."""

import json
import re
from decimal import Decimal
from html import escape
from importlib.resources import files

from options_analysis.experiments.adjustments import AdjustmentComparison


def _money(value: Decimal) -> str:
    return f"{'-' if value < 0 else ''}${abs(value):,.2f}"


def render_adjustment_report(result: AdjustmentComparison) -> str:
    """Render without external resources; input labels are always escaped."""
    reconciliation = "".join(
        f"<tr><th scope='row'>{escape(item.name)}</th>"
        f"<td>{_money(item.gross_cash_flow)}</td>"
        f"<td>{_money(item.transaction_fees)}</td>"
        f"<td>{_money(item.net_cash_flow)}</td>"
        f"<td>{_money(item.future_exit_fees)}</td>"
        f"<td>{len(item.remaining_legs)}</td></tr>"
        for item in result.alternatives
    )
    scenarios = "".join(
        f"<tr><th scope='row'>{escape(item.name)}</th>"
        f"<td>{_money(point.underlying_price)}</td>"
        f"<td>{_money(point.future_position_value)}</td>"
        f"<td>{_money(point.wealth)}</td>"
        f"<td>{_money(point.total_profit_loss)}</td>"
        f"<td>{_money(point.change_from_today)}</td>"
        f"<td>{_money(point.advantage_vs_hold)}</td></tr>"
        for index in range(len(result.alternatives[0].scenarios))
        for item in result.alternatives
        for point in (item.scenarios[index],)
    )
    ledgers = []
    for item in result.alternatives:
        rows = "".join(
            f"<tr><th scope='row'>{escape(flow.contract)}</th>"
            f"<td>{flow.quantity_change:+f}</td><td>{_money(flow.fill_price)}</td>"
            f"<td>{_money(flow.gross_cash_flow)}</td><td>{_money(flow.fees)}</td>"
            f"<td>{_money(flow.net_cash_flow)}</td></tr>"
            for flow in item.cash_flows
        )
        if not rows:
            rows = "<tr><td colspan='6'>No trades today.</td></tr>"
        positions = (
            "".join(
                "<li>"
                + escape(
                    f"{leg.quantity:+f} {leg.kind}"
                    + (
                        f" {leg.strike} · {leg.expiration}"
                        f" · multiplier {leg.multiplier}"
                        f" · IV {leg.implied_volatility:.2%}"
                        if leg.kind != "stock"
                        else " shares"
                    )
                )
                + "</li>"
                for leg in item.remaining_legs
            )
            or "<li>Cash only; no remaining position.</li>"
        )
        ledgers.append(
            f"<details><summary>{escape(item.name)}"
            " · trades and remaining position</summary>"
            "<div class='scroll'><table><caption>Today's cash-flow ledger</caption>"
            "<thead><tr><th>Contract</th><th>Signed trade</th><th>Fill / unit</th>"
            "<th>Gross cash</th><th>Fees</th><th>Net cash</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div><ul>{positions}</ul></details>"
        )
    warnings = "".join(f"<li>{escape(item)}</li>" for item in result.warnings)
    assumptions = "".join(f"<li>{escape(item)}</li>" for item in result.assumptions)
    # JSON script data cannot contain raw HTML delimiters, even in an inert
    # application/json element. This also prevents a label from closing script.
    payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    payload = (
        payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    )
    replacements = {
        "SYMBOL": escape(result.symbol),
        "ASOF": str(result.valuation_date),
        "HORIZON": str(result.horizon_date),
        "SPOT": _money(result.spot),
        "ENTRY": _money(result.entry_value),
        "ENTRY_FEES": _money(result.entry_fees),
        "CURRENT": _money(result.current_position_value),
        "CURRENT_PL": _money(result.current_profit_loss),
        "RECONCILIATION": reconciliation,
        "SCENARIOS": scenarios,
        "LEDGERS": "".join(ledgers),
        "WARNINGS": f"<ul>{warnings}</ul>"
        if warnings
        else "<p>No input/model warnings.</p>",
        "ASSUMPTIONS": assumptions,
        "DATA": payload,
    }

    def substitute(match: re.Match[str]) -> str:
        return replacements[match.group(1)]

    return re.sub(r"__([A-Z_]+)__", substitute, _TEMPLATE)


_TEMPLATE = (
    files("options_analysis.experiments")
    .joinpath("adjustment_report.html")
    .read_text(encoding="utf-8")
)
