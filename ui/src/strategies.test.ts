import { describe, expect, it } from "vitest";

import {
  buildTemplateDraft,
  StrategyBuildError,
  toAnalysisRequestLegs,
} from "./strategies";
import type {
  PutCall,
  Quote,
  StrategyTemplate,
  WorkspaceSnapshot,
} from "./types";

function option(side: PutCall, strike: number): Quote {
  const code = side === "call" ? "C" : "P";
  return {
    instrument: {
      asset_type: "option",
      symbol: `SPY-${code}-${strike}`,
      provider_id: "fake",
      provider_symbol: `SPY-${code}-${strike}`,
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
    bid: 1.9,
    ask: 2.1,
    last: 2,
    mark: 2,
    volume: 100,
    open_interest: 500,
    implied_volatility: 0.25,
    greeks: null,
    warnings: [],
  };
}

function workspace(): WorkspaceSnapshot {
  const underlying: Quote = {
    ...option("call", 100),
    instrument: {
      asset_type: "equity",
      symbol: "SPY",
      provider_id: "fake",
      provider_symbol: "SPY",
      option: null,
    },
    mark: 100,
  };
  const contracts = [90, 95, 100, 105, 110].flatMap((strike) => [
    option("put", strike),
    option("call", strike),
  ]);
  return {
    provider_id: "fake",
    symbol: "SPY",
    quote: underlying,
    expirations: ["2030-01-18"],
    chain: {
      provider_id: "fake",
      underlying_symbol: "SPY",
      as_of: underlying.as_of,
      underlying_quote: underlying,
      contracts,
      warnings: [],
    },
  };
}

function template(templateId: string): StrategyTemplate {
  return {
    template_id: templateId,
    display_name: templateId,
    description: templateId,
    outlook: "neutral",
    same_expiration: true,
    legs: [],
  };
}

describe("strategy template generation", () => {
  it("builds a covered call with signed intent and mark entries", () => {
    const legs = buildTemplateDraft(template("covered_call"), workspace());

    expect(legs.map((leg) => [leg.quote.instrument.asset_type, leg.action, leg.quantity])).toEqual([
      ["equity", "buy", 100],
      ["option", "sell", 1],
    ]);
    expect(legs[1].quote.instrument.option?.strike).toBe(100);
    expect(legs[0].entryPrice).toBe(100);
    expect(toAnalysisRequestLegs(legs).map((leg) => leg.quantity)).toEqual([100, -1]);
  });

  it("builds ordered vertical, butterfly, and condor legs", () => {
    const source = workspace();
    const strikes = (id: string) =>
      buildTemplateDraft(template(id), source).map(
        (leg) => leg.quote.instrument.option?.strike ?? "stock",
      );

    expect(strikes("bull_call_spread")).toEqual([100, 105]);
    expect(strikes("bear_put_spread")).toEqual([95, 100]);
    expect(strikes("long_call_butterfly")).toEqual([95, 100, 105]);
    expect(strikes("iron_condor")).toEqual([90, 95, 105, 110]);
  });

  it("explains when current chain filters omit required contracts", () => {
    const source = workspace();
    source.chain.contracts = source.chain.contracts.filter(
      (quote) => quote.instrument.option?.put_call === "call",
    );

    expect(() => buildTemplateDraft(template("iron_condor"), source)).toThrow(
      StrategyBuildError,
    );
  });
});
