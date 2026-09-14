import type {
  PutCall,
  WatchlistResult,
  WorkspaceResult,
  WorkspaceSnapshot,
} from "./types";

interface WorkspaceQuery {
  expiration?: string;
  putCall?: PutCall | "all";
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
