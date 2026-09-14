import { decimal } from "./chain";
import { payoffGeometry } from "./payoff";
import type { DecimalValue, PositionAnalysis } from "./types";

interface Props {
  analysis: PositionAnalysis | null;
  loading: boolean;
  error: string | null;
}

function money(value: DecimalValue | null | undefined): string {
  const parsed = decimal(value);
  return parsed === null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(parsed);
}

function signed(value: DecimalValue | null | undefined, digits = 1): string {
  const parsed = decimal(value);
  return parsed === null ? "—" : parsed.toFixed(digits);
}

function riskValue(
  value: DecimalValue | null,
  bounded: boolean | null,
  unlimitedLabel: string,
): string {
  if (bounded === false) return unlimitedLabel;
  return money(value);
}

function premiumLabel(value: DecimalValue | null): string {
  const parsed = decimal(value);
  if (parsed === null) return "—";
  return parsed >= 0 ? `${money(parsed)} debit` : `${money(Math.abs(parsed))} credit`;
}

export default function AnalysisPanel({ analysis, loading, error }: Props) {
  if (error) return <div className="analysis-error" role="alert">{error}</div>;
  if (loading) {
    return <div className="analysis-empty" role="status">Calculating combined position…</div>;
  }
  if (!analysis) {
    return (
      <div className="analysis-empty">
        Choose a template or add contracts to calculate combined risk.
      </div>
    );
  }

  const chart = payoffGeometry(analysis.payoff_points);
  const greeks = analysis.aggregate_greeks;
  return (
    <div className="combined-analysis">
      <div className="risk-grid">
        <div><span>Entry</span><strong>{premiumLabel(analysis.net_cost_basis)}</strong></div>
        <div><span>Max profit</span><strong>{riskValue(analysis.max_profit, analysis.max_profit_bounded, "Unlimited")}</strong></div>
        <div><span>Max loss</span><strong>{riskValue(analysis.max_loss, analysis.max_loss_bounded, "Unlimited")}</strong></div>
        <div><span>Break-even</span><strong>{analysis.break_even_prices.map((value) => money(value)).join(", ") || "—"}</strong></div>
      </div>

      <div className="greek-grid">
        {(["delta", "gamma", "theta", "vega"] as const).map((name) => (
          <div className={greeks[name].complete ? "" : "incomplete"} key={name}>
            <span>{name}</span>
            <strong>{signed(greeks[name].value, 2)}</strong>
          </div>
        ))}
      </div>

      <div className="payoff-card">
        <div className="draft-heading">
          <span className="eyebrow">Expiration payoff</span>
          <span>{analysis.expiration_date ?? "Multiple dates"}</span>
        </div>
        {chart ? (
          <>
            <svg
              aria-label="Expiration profit and loss chart"
              className="payoff-chart"
              role="img"
              viewBox="0 0 440 180"
            >
              <line className="zero-line" x1="18" x2="422" y1={chart.zeroY} y2={chart.zeroY} />
              <polyline className="payoff-line" points={chart.points} />
            </svg>
            <div className="chart-axis">
              <span>{money(chart.minX)}</span>
              <span>P/L {money(chart.minY)} to {money(chart.maxY)}</span>
              <span>{money(chart.maxX)}</span>
            </div>
          </>
        ) : (
          <p className="draft-empty">A single expiration and complete entry prices are required.</p>
        )}
      </div>

      <div className="scenario-card">
        <span className="eyebrow">Delta-gamma scenarios</span>
        <div className="scenario-row scenario-heading">
          <span>Move</span><span>Underlying</span><span>Estimated P/L</span>
        </div>
        {analysis.scenarios.map((scenario) => (
          <div className="scenario-row" key={String(scenario.underlying_change)}>
            <span>{signed((decimal(scenario.underlying_change) ?? 0) * 100, 0)}%</span>
            <span>{money(scenario.underlying_price)}</span>
            <strong>{money(scenario.estimated_profit_loss)}</strong>
          </div>
        ))}
      </div>

      {analysis.warnings.length || analysis.assumptions.length ? (
        <details className="analysis-notes">
          <summary>Assumptions and warnings ({analysis.warnings.length})</summary>
          {analysis.warnings.map((warning) => (
            <p key={`${warning.code}-${warning.message}`}>{warning.message}</p>
          ))}
          {analysis.assumptions.map((assumption) => <p key={assumption}>{assumption}</p>)}
        </details>
      ) : null}
    </div>
  );
}
