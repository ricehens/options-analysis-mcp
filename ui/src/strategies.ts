import { decimal } from "./chain";
import type {
  AnalysisRequestLeg,
  Quote,
  StrategyTemplate,
  WorkspaceSnapshot,
} from "./types";

export interface DraftLeg {
  quote: Quote;
  action: "buy" | "sell";
  quantity: number;
  entryPrice: number;
}

export class StrategyBuildError extends Error {}

export function toAnalysisRequestLegs(legs: DraftLeg[]): AnalysisRequestLeg[] {
  return legs.map((leg) => ({
    symbol: leg.quote.instrument.provider_symbol,
    asset_type: leg.quote.instrument.asset_type,
    quantity: leg.action === "buy" ? leg.quantity : -leg.quantity,
    average_open_price: leg.entryPrice,
  }));
}

function entryPrice(quote: Quote): number {
  const mark = decimal(quote.mark);
  if (mark !== null) return mark;
  const bid = decimal(quote.bid);
  const ask = decimal(quote.ask);
  if (bid !== null && ask !== null) return (bid + ask) / 2;
  const last = decimal(quote.last);
  if (last !== null) return last;
  throw new StrategyBuildError(
    `${quote.instrument.provider_symbol} has no usable entry price.`,
  );
}

export function draftFromQuote(
  quote: Quote,
  action: "buy" | "sell" = "buy",
  quantity = 1,
): DraftLeg {
  return { quote, action, quantity, entryPrice: entryPrice(quote) };
}

function optionQuotes(workspace: WorkspaceSnapshot, side: "call" | "put"): Quote[] {
  return workspace.chain.contracts
    .filter((quote) => quote.instrument.option?.put_call === side)
    .sort(
      (left, right) =>
        Number(left.instrument.option?.strike) - Number(right.instrument.option?.strike),
    );
}

function nearestIndex(quotes: Quote[], spot: number): number {
  if (!quotes.length) return -1;
  return quotes.reduce((best, quote, index) => {
    const distance = Math.abs(Number(quote.instrument.option?.strike) - spot);
    const bestDistance = Math.abs(
      Number(quotes[best].instrument.option?.strike) - spot,
    );
    return distance < bestDistance ? index : best;
  }, 0);
}

function requireQuote(quote: Quote | undefined, message: string): Quote {
  if (!quote) throw new StrategyBuildError(message);
  return quote;
}

export function buildTemplateDraft(
  template: StrategyTemplate,
  workspace: WorkspaceSnapshot,
  existing: DraftLeg[] = [],
): DraftLeg[] {
  if (template.template_id === "custom") return existing;
  const spot = decimal(workspace.quote.mark);
  if (spot === null) throw new StrategyBuildError("Underlying mark is unavailable.");
  const calls = optionQuotes(workspace, "call");
  const puts = optionQuotes(workspace, "put");
  const callIndex = nearestIndex(calls, spot);
  const putIndex = nearestIndex(puts, spot);

  switch (template.template_id) {
    case "long_call":
      return [
        draftFromQuote(requireQuote(calls[callIndex], "Load at least one call.")),
      ];
    case "long_put":
      return [draftFromQuote(requireQuote(puts[putIndex], "Load at least one put."))];
    case "covered_call": {
      const shortCall = calls.find(
        (quote) => Number(quote.instrument.option?.strike) >= spot,
      );
      return [
        draftFromQuote(workspace.quote, "buy", 100),
        draftFromQuote(
          requireQuote(shortCall, "Load a call at or above spot."),
          "sell",
        ),
      ];
    }
    case "bull_call_spread":
      return [
        draftFromQuote(requireQuote(calls[callIndex], "Load two adjacent calls.")),
        draftFromQuote(
          requireQuote(calls[callIndex + 1], "Load a higher call."),
          "sell",
        ),
      ];
    case "bear_put_spread":
      return [
        draftFromQuote(
          requireQuote(puts[putIndex - 1], "Load a lower put."),
          "sell",
        ),
        draftFromQuote(requireQuote(puts[putIndex], "Load two adjacent puts.")),
      ];
    case "long_call_butterfly":
      return [
        draftFromQuote(requireQuote(calls[callIndex - 1], "Load calls around spot.")),
        draftFromQuote(
          requireQuote(calls[callIndex], "Load three adjacent calls."),
          "sell",
          2,
        ),
        draftFromQuote(requireQuote(calls[callIndex + 1], "Load calls around spot.")),
      ];
    case "iron_condor": {
      const lowerPuts = puts.filter(
        (quote) => Number(quote.instrument.option?.strike) < spot,
      );
      const higherCalls = calls.filter(
        (quote) => Number(quote.instrument.option?.strike) > spot,
      );
      return [
        draftFromQuote(
          requireQuote(lowerPuts.at(-2), "Load two put strikes below spot."),
        ),
        draftFromQuote(
          requireQuote(lowerPuts.at(-1), "Load two put strikes below spot."),
          "sell",
        ),
        draftFromQuote(
          requireQuote(higherCalls[0], "Load two call strikes above spot."),
          "sell",
        ),
        draftFromQuote(
          requireQuote(higherCalls[1], "Load two call strikes above spot."),
        ),
      ];
    }
    default:
      throw new StrategyBuildError(`Unsupported strategy ${template.template_id}.`);
  }
}
