export type DecimalValue = string | number;
export type PutCall = "call" | "put";

export interface ErrorDetail {
  category: string;
  message: string;
  retryable: boolean;
  reauthorization_required: boolean;
  field_paths: string[];
}

export interface OptionTerms {
  underlying_symbol: string;
  expiration_date: string;
  put_call: PutCall;
  strike: DecimalValue;
  multiplier: DecimalValue;
}

export interface Instrument {
  asset_type: string;
  symbol: string;
  provider_id: string;
  provider_symbol: string;
  option: OptionTerms | null;
}

export interface Greeks {
  delta: DecimalValue | null;
  gamma: DecimalValue | null;
  theta: DecimalValue | null;
  vega: DecimalValue | null;
  rho: DecimalValue | null;
}

export interface Quote {
  instrument: Instrument;
  provider_id: string;
  as_of: string;
  received_at: string;
  bid: DecimalValue | null;
  ask: DecimalValue | null;
  last: DecimalValue | null;
  mark: DecimalValue | null;
  volume: number | null;
  open_interest: number | null;
  implied_volatility: DecimalValue | null;
  greeks: Greeks | null;
  warnings: Array<{ code: string; message: string }>;
}

export interface OptionChain {
  provider_id: string;
  underlying_symbol: string;
  as_of: string;
  underlying_quote: Quote | null;
  contracts: Quote[];
  warnings: Array<{ code: string; message: string }>;
}

export interface WorkspaceSnapshot {
  provider_id: string;
  symbol: string;
  quote: Quote;
  expirations: string[];
  chain: OptionChain;
}

export interface WorkspaceResult {
  workspace: WorkspaceSnapshot | null;
  error: ErrorDetail | null;
}
