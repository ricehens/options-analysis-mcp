import type { Quote } from "./types";

export interface ChainRow {
  strike: number;
  call?: Quote;
  put?: Quote;
}

export type MoneynessRange = "all" | "2.5" | "5" | "10";
export type SortKey =
  | "strike"
  | "call_iv"
  | "call_open_interest"
  | "put_iv"
  | "put_open_interest";
export type SortDirection = "asc" | "desc";

export interface ChainFilters {
  moneynessRange: MoneynessRange;
  minOpenInterest: number;
  maxSpreadPercent: number | null;
}

export function decimal(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function buildChainRows(contracts: Quote[]): ChainRow[] {
  const indexed = new Map<number, ChainRow>();
  for (const contract of contracts) {
    const terms = contract.instrument.option;
    if (!terms) continue;
    const strike = Number(terms.strike);
    const row = indexed.get(strike) ?? { strike };
    row[terms.put_call] = contract;
    indexed.set(strike, row);
  }
  return [...indexed.values()].sort((left, right) => left.strike - right.strike);
}

export function spreadPercent(quote: Quote | undefined): number | null {
  const bid = decimal(quote?.bid);
  const ask = decimal(quote?.ask);
  if (bid === null || ask === null || ask < bid) return null;
  const midpoint = (bid + ask) / 2;
  return midpoint > 0 ? ((ask - bid) / midpoint) * 100 : null;
}

function quotePassesLiquidity(quote: Quote | undefined, filters: ChainFilters): boolean {
  if (!quote) return false;
  if ((quote.open_interest ?? 0) < filters.minOpenInterest) return false;
  const spread = spreadPercent(quote);
  return (
    filters.maxSpreadPercent === null ||
    (spread !== null && spread <= filters.maxSpreadPercent)
  );
}

export function filterChainRows(
  rows: ChainRow[],
  underlyingPrice: number | null,
  filters: ChainFilters,
): ChainRow[] {
  const range = filters.moneynessRange === "all" ? null : Number(filters.moneynessRange);
  return rows.flatMap((row) => {
    const distance =
      underlyingPrice && underlyingPrice > 0
        ? (Math.abs(row.strike - underlyingPrice) / underlyingPrice) * 100
        : null;
    if (range !== null && (distance === null || distance > range)) return [];
    const filtered: ChainRow = {
      strike: row.strike,
      call: quotePassesLiquidity(row.call, filters) ? row.call : undefined,
      put: quotePassesLiquidity(row.put, filters) ? row.put : undefined,
    };
    return filtered.call || filtered.put ? [filtered] : [];
  });
}

function sortableValue(row: ChainRow, key: SortKey): number | null {
  if (key === "strike") return row.strike;
  if (key === "call_iv") return decimal(row.call?.implied_volatility);
  if (key === "put_iv") return decimal(row.put?.implied_volatility);
  if (key === "call_open_interest") return row.call?.open_interest ?? null;
  return row.put?.open_interest ?? null;
}

export function sortChainRows(
  rows: ChainRow[],
  key: SortKey,
  direction: SortDirection,
): ChainRow[] {
  const multiplier = direction === "asc" ? 1 : -1;
  return [...rows].sort((left, right) => {
    const leftValue = sortableValue(left, key);
    const rightValue = sortableValue(right, key);
    if (leftValue === null && rightValue === null) return left.strike - right.strike;
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    return (leftValue - rightValue || left.strike - right.strike) * multiplier;
  });
}

export function moneynessPercent(strike: number, underlyingPrice: number | null): number | null {
  return underlyingPrice && underlyingPrice > 0
    ? ((strike - underlyingPrice) / underlyingPrice) * 100
    : null;
}

export function daysToExpiration(expiration: string, today = new Date()): number {
  const target = Date.parse(`${expiration}T00:00:00Z`);
  const start = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Math.ceil((target - start) / 86_400_000);
}
