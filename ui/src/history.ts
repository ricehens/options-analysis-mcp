import { decimal } from "./chain";
import type {
  DecimalValue,
  HistoryResolution,
  PriceBar,
  TechnicalIndicatorPoint,
} from "./types";

export const DEFAULT_PRICE_INDICATORS = [
  { spec: "sma:20", label: "SMA 20", styleIndex: 1 },
  { spec: "sma:50", label: "SMA 50", styleIndex: 2 },
] as const;

export const HISTORY_VIEWS: ReadonlyArray<{
  resolution: HistoryResolution;
  label: string;
  description: string;
}> = [
  { resolution: "1m", label: "1m", description: "One-minute bars, one day" },
  { resolution: "5m", label: "5m", description: "Five-minute bars, one week" },
  { resolution: "1d", label: "1D", description: "Daily bars, one year" },
  { resolution: "1w", label: "1W", description: "Weekly bars, five years" },
  { resolution: "1mo", label: "1M", description: "Monthly bars, twenty years" },
];

export interface PriceChartPoint {
  x: number;
  y: number;
  bar: PriceBar;
  close: number;
}

export interface PriceChartGeometry {
  points: PriceChartPoint[];
  linePath: string;
  areaPath: string;
  minimum: number;
  maximum: number;
  ticks: Array<{ value: number; y: number }>;
}

export const PRICE_CHART_BOX = {
  width: 800,
  height: 244,
  left: 68,
  right: 782,
  top: 18,
  bottom: 202,
} as const;

function rounded(value: number): number {
  return Math.round(value * 100) / 100;
}

export function buildPriceChart(
  bars: PriceBar[],
  overlayValues: DecimalValue[] = [],
): PriceChartGeometry | null {
  const usable = bars.flatMap((bar) => {
    const close = decimal(bar.close);
    const low = decimal(bar.low);
    const high = decimal(bar.high);
    return close === null || low === null || high === null
      ? []
      : [{ bar, close, low, high }];
  });
  if (!usable.length) return null;

  let minimum = Math.min(...usable.map((point) => point.low));
  let maximum = Math.max(...usable.map((point) => point.high));
  const overlayNumbers = overlayValues.flatMap((value) => {
    const parsed = decimal(value);
    return parsed === null ? [] : [parsed];
  });
  if (overlayNumbers.length) {
    minimum = Math.min(minimum, ...overlayNumbers);
    maximum = Math.max(maximum, ...overlayNumbers);
  }
  if (maximum === minimum) {
    const padding = Math.max(Math.abs(maximum) * 0.005, 0.5);
    minimum -= padding;
    maximum += padding;
  }

  const horizontalSpan = PRICE_CHART_BOX.right - PRICE_CHART_BOX.left;
  const verticalSpan = PRICE_CHART_BOX.bottom - PRICE_CHART_BOX.top;
  const points = usable.map(({ bar, close }, index) => ({
    x: rounded(
      PRICE_CHART_BOX.left +
        (horizontalSpan * index) / Math.max(usable.length - 1, 1),
    ),
    y: rounded(
      PRICE_CHART_BOX.top +
        ((maximum - close) / (maximum - minimum)) * verticalSpan,
    ),
    bar,
    close,
  }));
  const linePath = points
    .map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`)
    .join(" ");
  const first = points[0];
  const last = points.at(-1) ?? first;
  const areaPath = `${linePath} L ${last.x} ${PRICE_CHART_BOX.bottom} L ${first.x} ${PRICE_CHART_BOX.bottom} Z`;
  const ticks = [maximum, (maximum + minimum) / 2, minimum].map(
    (value, index) => ({
      value,
      y: rounded(PRICE_CHART_BOX.top + (verticalSpan * index) / 2),
    }),
  );

  return { points, linePath, areaPath, minimum, maximum, ticks };
}

export function buildIndicatorPath(
  points: TechnicalIndicatorPoint[],
  bars: PriceBar[],
  minimum: number,
  maximum: number,
): string {
  if (maximum <= minimum || !bars.length) return "";
  const indexes = new Map(
    bars.map((bar, index) => [Date.parse(bar.start), index] as const),
  );
  const horizontalSpan = PRICE_CHART_BOX.right - PRICE_CHART_BOX.left;
  const verticalSpan = PRICE_CHART_BOX.bottom - PRICE_CHART_BOX.top;
  return points
    .flatMap((point) => {
      const index = indexes.get(Date.parse(point.timestamp));
      const value = decimal(point.value);
      if (index === undefined || value === null) return [];
      return [
        {
          x: rounded(
            PRICE_CHART_BOX.left +
              (horizontalSpan * index) / Math.max(bars.length - 1, 1),
          ),
          y: rounded(
            PRICE_CHART_BOX.top +
              ((maximum - value) / (maximum - minimum)) * verticalSpan,
          ),
        },
      ];
    })
    .map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`)
    .join(" ");
}

export function priceChange(bars: PriceBar[]): {
  amount: number;
  percent: number | null;
} | null {
  const first = decimal(bars[0]?.close);
  const last = decimal(bars.at(-1)?.close);
  if (first === null || last === null) return null;
  const amount = last - first;
  return { amount, percent: first === 0 ? null : amount / first };
}
