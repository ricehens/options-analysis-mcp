import type {
  AnalysisRequestLeg,
  PositionAnalysis,
  PositionAnalysisResult,
  PutCall,
  StrategyCatalogResult,
  StrategyTemplate,
  WatchlistResult,
  WorkspaceResult,
  WorkspaceSnapshot,
} from "./types";

interface WorkspaceQuery {
  expiration?: string;
  putCall?: PutCall | "all";
  strikeFrom?: number;
  strikeTo?: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly category = "unknown",
  ) {
    super(message);
  }
}

export async function loadWorkspace(
  symbol: string,
  query: WorkspaceQuery,
  signal?: AbortSignal,
): Promise<WorkspaceSnapshot> {
  const params = new URLSearchParams({ limit: "100" });
  if (query.expiration) params.set("expiration", query.expiration);
  if (query.putCall && query.putCall !== "all") {
    params.set("put_call", query.putCall);
  }
  if (query.strikeFrom !== undefined) {
    params.set("strike_from", String(query.strikeFrom));
  }
  if (query.strikeTo !== undefined) {
    params.set("strike_to", String(query.strikeTo));
  }
  const response = await fetch(
    `/api/v1/workspaces/${encodeURIComponent(symbol)}?${params}`,
    { signal },
  );
  const result = (await response.json()) as WorkspaceResult;
  if (!response.ok || result.error) {
    throw new ApiError(
      result.error?.message ?? `Request failed (${response.status})`,
      result.error?.category,
    );
  }
  if (!result.workspace) throw new ApiError("The API returned no workspace data.");
  return result.workspace;
}

async function watchlistRequest(
  path: string,
  init?: RequestInit,
): Promise<string[]> {
  const response = await fetch(path, init);
  const result = (await response.json()) as WatchlistResult;
  if (!response.ok || result.error) {
    throw new ApiError(
      result.error?.message ?? `Request failed (${response.status})`,
      result.error?.category,
    );
  }
  return result.items.map((item) => item.symbol);
}

export function loadWatchlist(signal?: AbortSignal): Promise<string[]> {
  return watchlistRequest("/api/v1/watchlist", { signal });
}

export function addWatchlistSymbol(symbol: string): Promise<string[]> {
  return watchlistRequest("/api/v1/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
  });
}

export function deleteWatchlistSymbol(symbol: string): Promise<string[]> {
  return watchlistRequest(`/api/v1/watchlist/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
}

export async function loadStrategies(signal?: AbortSignal): Promise<StrategyTemplate[]> {
  const response = await fetch("/api/v1/strategies", { signal });
  const result = (await response.json()) as StrategyCatalogResult;
  if (!response.ok || result.error) {
    throw new ApiError(
      result.error?.message ?? `Request failed (${response.status})`,
      result.error?.category,
    );
  }
  return result.strategies;
}

export async function analyzePositions(
  legs: AnalysisRequestLeg[],
  provider: string,
  signal?: AbortSignal,
): Promise<PositionAnalysis> {
  const response = await fetch("/api/v1/analyses/positions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ legs, provider }),
    signal,
  });
  const result = (await response.json()) as PositionAnalysisResult;
  if (!response.ok || result.error) {
    throw new ApiError(
      result.error?.message ?? `Request failed (${response.status})`,
      result.error?.category,
    );
  }
  if (!result.analysis) throw new ApiError("The API returned no analysis.");
  return result.analysis;
}
