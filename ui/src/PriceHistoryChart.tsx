import { useId, useMemo } from "react";

import {
  buildPriceChart,
  HISTORY_VIEWS,
  PRICE_CHART_BOX,
  priceChange,
} from "./history";
import type { HistoryResolution, PriceHistorySnapshot } from "./types";

interface PriceHistoryChartProps {
  error: string | null;
  history: PriceHistorySnapshot | null;
  loading: boolean;
  onResolutionChange: (resolution: HistoryResolution) => void;
  resolution: HistoryResolution;
  symbol: string;
}

function dollars(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

function timestamp(value: string | undefined, resolution: HistoryResolution): string {
  if (!value) return "—";
  const date = new Date(value);
  return new Intl.DateTimeFormat(
    "en-US",
    resolution === "1m" || resolution === "5m"
      ? { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }
      : { month: "short", day: "numeric", year: "numeric" },
  ).format(date);
}

export default function PriceHistoryChart({
  error,
  history,
  loading,
  onResolutionChange,
  resolution,
  symbol,
}: PriceHistoryChartProps) {
  const titleId = useId();
  const descriptionId = useId();
  const bars = history?.bars ?? [];
  const geometry = useMemo(() => buildPriceChart(bars), [bars]);
  const change = priceChange(bars);
  const last = geometry?.points.at(-1);
  const changeDirection = !change
    ? "neutral"
    : change.amount > 0
      ? "positive"
      : change.amount < 0
        ? "negative"
        : "neutral";
  const firstTimestamp = timestamp(bars[0]?.start, resolution);
  const lastTimestamp = timestamp(bars.at(-1)?.start, resolution);

  return (
    <section aria-busy={loading} className="panel price-history-panel">
      <header className="price-history-header">
        <div>
          <span className="eyebrow">Underlying history</span>
          <div className="history-title-row">
            <h2>{symbol || "No symbol"} price</h2>
            {last ? <strong>{dollars(last.close)}</strong> : null}
            {change ? (
              <span className={`history-change ${changeDirection}`}>
                {change.amount >= 0 ? "+" : ""}{dollars(change.amount)}
                {change.percent === null
                  ? ""
                  : ` (${change.percent >= 0 ? "+" : ""}${(
                      change.percent * 100
                    ).toFixed(2)}%)`}
              </span>
            ) : null}
          </div>
        </div>
        <div aria-label="Price interval" className="history-tabs" role="group">
          {HISTORY_VIEWS.map((view) => (
            <button
              aria-label={view.description}
              aria-pressed={resolution === view.resolution}
              className={resolution === view.resolution ? "selected" : ""}
              key={view.resolution}
              onClick={() => onResolutionChange(view.resolution)}
              type="button"
            >
              {view.label}
            </button>
          ))}
        </div>
      </header>

      {error ? (
        <div className="history-message error" role="alert">{error}</div>
      ) : !geometry ? (
        <div className="history-message" role="status">
          {loading ? "Loading price history…" : "No price history is available."}
        </div>
      ) : (
        <div aria-live="polite" className={loading ? "history-chart loading" : "history-chart"}>
          <svg
            aria-describedby={descriptionId}
            aria-labelledby={titleId}
            className="price-chart-svg"
            role="img"
            viewBox={`0 0 ${PRICE_CHART_BOX.width} ${PRICE_CHART_BOX.height}`}
          >
            <title id={titleId}>{`${symbol} closing-price history`}</title>
            <desc id={descriptionId}>
              {bars.length} {resolution} price bars from {firstTimestamp} through {lastTimestamp}.
              {change ? ` Net change ${dollars(change.amount)}.` : ""}
            </desc>
            <defs>
              <linearGradient id="price-history-area" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.2" />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
              </linearGradient>
            </defs>
            {geometry.ticks.map((tick) => (
              <g key={tick.y}>
                <line
                  className="history-grid-line"
                  x1={PRICE_CHART_BOX.left}
                  x2={PRICE_CHART_BOX.right}
                  y1={tick.y}
                  y2={tick.y}
                />
                <text
                  className="history-axis-label"
                  textAnchor="end"
                  x={PRICE_CHART_BOX.left - 9}
                  y={tick.y + 4}
                >
                  {dollars(tick.value)}
                </text>
              </g>
            ))}
            <path className="history-area" d={geometry.areaPath} />
            <path className="history-line" d={geometry.linePath} />
            {last ? (
              <circle
                aria-hidden="true"
                className="history-last-point"
                cx={last.x}
                cy={last.y}
                r="4"
              />
            ) : null}
            <text className="history-time-label" x={PRICE_CHART_BOX.left} y="232">
              {firstTimestamp}
            </text>
            <text
              className="history-time-label"
              textAnchor="end"
              x={PRICE_CHART_BOX.right}
              y="232"
            >
              {lastTimestamp}
            </text>
          </svg>
          <div className="history-caption">
            <span>{bars.length} bars · {history?.provider_id}</span>
            <span>
              Range {dollars(geometry.minimum)}–{dollars(geometry.maximum)}
              {history?.truncated ? " · latest 500 shown" : ""}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
