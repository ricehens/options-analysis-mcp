import { describe, expect, it } from "vitest";

import { payoffGeometry } from "./payoff";

describe("payoff chart geometry", () => {
  it("projects price/profit points and a zero axis into a bounded view box", () => {
    const chart = payoffGeometry([
      { underlying_price: 90, position_value: 0, profit_loss: -200 },
      { underlying_price: 100, position_value: 300, profit_loss: 100 },
      { underlying_price: 110, position_value: 0, profit_loss: -200 },
    ]);

    expect(chart).not.toBeNull();
    expect(chart?.points.split(" ")).toHaveLength(3);
    expect(chart?.minX).toBe(90);
    expect(chart?.maxX).toBe(110);
    expect(chart?.zeroY).toBeGreaterThan(18);
    expect(chart?.zeroY).toBeLessThan(162);
  });

  it("returns no geometry for insufficient usable data", () => {
    expect(payoffGeometry([])).toBeNull();
    expect(
      payoffGeometry([
        { underlying_price: 100, position_value: 0, profit_loss: null },
      ]),
    ).toBeNull();
  });
});
