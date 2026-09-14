import type { PutCall, WorkspaceResult, WorkspaceSnapshot } from "./types";

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
