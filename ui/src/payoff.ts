import { decimal } from "./chain";
import type { PositionAnalysis } from "./types";

type PayoffPoint = PositionAnalysis["payoff_points"][number];

export interface PayoffGeometry {
  points: string;
  zeroY: number;
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export function payoffGeometry(
  source: PayoffPoint[],
  width = 440,
  height = 180,
  padding = 18,
): PayoffGeometry | null {
  const values = source.flatMap((point) => {
    const x = decimal(point.underlying_price);
    const y = decimal(point.profit_loss);
    return x === null || y === null ? [] : [{ x, y }];
  });
  if (values.length < 2) return null;
  const minX = Math.min(...values.map((point) => point.x));
  const maxX = Math.max(...values.map((point) => point.x));
  let minY = Math.min(0, ...values.map((point) => point.y));
  let maxY = Math.max(0, ...values.map((point) => point.y));
  if (minX === maxX) return null;
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;
  const projectX = (value: number) =>
    padding + ((value - minX) / (maxX - minX)) * plotWidth;
  const projectY = (value: number) =>
    padding + ((maxY - value) / (maxY - minY)) * plotHeight;
  return {
    points: values
      .map((point) => `${projectX(point.x).toFixed(2)},${projectY(point.y).toFixed(2)}`)
      .join(" "),
    zeroY: projectY(0),
    minX,
    maxX,
    minY,
    maxY,
  };
}
