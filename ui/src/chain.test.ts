import { describe, expect, it } from "vitest";

import {
  buildChainRows,
  daysToExpiration,
  filterChainRows,
  sortChainRows,
  spreadPercent,
} from "./chain";
import type { PutCall, Quote } from "./types";

function option(
  side: PutCall,
  strike: number,
  options: { bid?: number; ask?: number; iv?: number; openInterest?: number } = {},
): Quote {
  return {
    instrument: {
      asset_type: "option",
      symbol: `SPY-${side}-${strike}`,
      provider_id: "fake",
      provider_symbol: `SPY-${side}-${strike}`,
      option: {
        underlying_symbol: "SPY",
        expiration_date: "2030-01-18",
        put_call: side,
        strike,
        multiplier: 100,
      },
    },
    provider_id: "fake",
    as_of: "2026-01-02T15:30:00Z",
    received_at: "2026-01-02T15:30:00Z",
    bid: options.bid ?? 1.9,
    ask: options.ask ?? 2.1,
    last: 2,
    mark: 2,
    volume: 100,
    open_interest: options.openInterest ?? 500,
    implied_volatility: options.iv ?? 0.25,
    greeks: null,
    warnings: [],
  };
}

describe("chain view model", () => {
  it("pairs calls and puts by strike", () => {
    const rows = buildChainRows([
      option("put", 100),
      option("call", 95),
      option("call", 100),
    ]);

    expect(rows.map((row) => row.strike)).toEqual([95, 100]);
    expect(rows[0].call?.instrument.option?.put_call).toBe("call");
    expect(rows[0].put).toBeUndefined();
    expect(rows[1].put?.instrument.option?.put_call).toBe("put");
  });

  it("filters by distance, open interest, and spread", () => {
    const rows = buildChainRows([
      option("call", 95, { openInterest: 10 }),
      option("call", 100, { bid: 1.99, ask: 2.01, openInterest: 900 }),
      option("call", 110, { openInterest: 900 }),
    ]);

    const filtered = filterChainRows(rows, 100, {
      moneynessRange: "5",
      minOpenInterest: 100,
      maxSpreadPercent: 2,
    });

    expect(filtered.map((row) => row.strike)).toEqual([100]);
    expect(spreadPercent(filtered[0].call)).toBeCloseTo(1);
    expect(filtered[0].put).toBeUndefined();
  });

  it("sorts provider values and leaves missing values last", () => {
    const rows = buildChainRows([
      option("call", 95, { iv: 0.3 }),
      option("call", 100, { iv: 0.2 }),
      option("put", 105, { iv: 0.1 }),
    ]);

    expect(sortChainRows(rows, "call_iv", "asc").map((row) => row.strike)).toEqual([
      100,
      95,
      105,
    ]);
  });

  it("calculates DTE using UTC calendar dates", () => {
    expect(daysToExpiration("2026-01-12", new Date("2026-01-02T23:00:00Z"))).toBe(10);
  });
});
