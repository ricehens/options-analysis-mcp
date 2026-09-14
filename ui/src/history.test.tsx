import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import PriceHistoryChart from "./PriceHistoryChart";
import { buildPriceChart, HISTORY_VIEWS, PRICE_CHART_BOX, priceChange } from "./history";
import type { PriceBar, PriceHistorySnapshot } from "./types";

const instrument = {
  asset_type: "equity",
  symbol: "SPY",
  provider_id: "fake",
  provider_symbol: "SPY",
  option: null,
};

function bar(index: number, close: number): PriceBar {
  return {
    provider_id: "fake",
    instrument,
    start: `2026-09-${String(index + 10).padStart(2, "0")}T12:00:00Z`,
    end: `2026-09-${String(index + 11).padStart(2, "0")}T12:00:00Z`,
    open: close - 0.25,
    high: close + 1,
    low: close - 1,
    close,
    volume: 1_000_000 + index,
  };
}

const bars = [bar(0, 100), bar(1, 105), bar(2, 102)];

describe("price history chart", () => {
  it("provides all requested intervals and their bounded context", () => {
    expect(HISTORY_VIEWS.map((view) => view.resolution)).toEqual([
      "1m",
      "5m",
      "1d",
      "1w",
      "1mo",
    ]);
    expect(HISTORY_VIEWS.map((view) => view.description)).toEqual([
      "One-minute bars, one day",
      "Five-minute bars, one week",
      "Daily bars, one year",
      "Weekly bars, five years",
      "Monthly bars, twenty years",
    ]);
  });

  it("maps normalized OHLC values into bounded line and area geometry", () => {
    const chart = buildPriceChart(bars);

    expect(chart).not.toBeNull();
    expect(chart?.points).toHaveLength(3);
    expect(chart?.points[0].x).toBe(PRICE_CHART_BOX.left);
    expect(chart?.points.at(-1)?.x).toBe(PRICE_CHART_BOX.right);
    expect(chart?.points.every((point) => point.y >= PRICE_CHART_BOX.top)).toBe(true);
    expect(chart?.points.every((point) => point.y <= PRICE_CHART_BOX.bottom)).toBe(true);
    expect(chart?.linePath).toMatch(/^M /);
    expect(chart?.areaPath).toMatch(/ Z$/);
    expect(chart?.ticks).toHaveLength(3);
  });

  it("handles empty, flat, and percent-change series", () => {
    expect(buildPriceChart([])).toBeNull();
    const flat = buildPriceChart([bar(0, 100), bar(1, 100)]);
    expect(flat?.minimum).toBeLessThan(flat?.maximum ?? 0);
    expect(priceChange(bars)).toEqual({ amount: 2, percent: 0.02 });
  });

  it("renders a labelled chart and pressed interval control", () => {
    const history: PriceHistorySnapshot = {
      provider_id: "fake",
      symbol: "SPY",
      resolution: "1d",
      start: bars[0].start,
      end: bars.at(-1)?.end ?? bars[0].end,
      bars,
      truncated: false,
    };
    const markup = renderToStaticMarkup(
      <PriceHistoryChart
        error={null}
        history={history}
        loading={false}
        onResolutionChange={() => undefined}
        resolution="1d"
        symbol="SPY"
      />,
    );

    expect(markup).toContain("SPY closing-price history");
    expect(markup).toContain("3 1d price bars");
    expect(markup).toContain("aria-label=\"Daily bars, one year\"");
    expect(markup).toContain("aria-pressed=\"true\"");
    expect(markup).toContain("+$2.00 (+2.00%)");
  });
});
