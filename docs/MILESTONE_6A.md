# Milestone 6A — Browser Foundation

Completed in code: 2026-09-14

## Delivered

- A local-only FastAPI interface under `/api/v1` that imports the same
  `Application` services used by MCP.
- Server-info and provider-discovery endpoints.
- A combined selected-symbol workspace endpoint returning the underlying
  quote, expiration list, and a bounded filtered option chain.
- Transport-neutral, structured errors shared by the HTTP and MCP adapters.
- A responsive React/TypeScript/Vite application with:
  - an editable in-memory watchlist;
  - selected-symbol quote details;
  - expiration and call/put filters;
  - a paired call/put option-chain table;
  - a strategy-template preview panel.
- Local API proxying for development without putting provider credentials in
  the browser.

## Boundary decisions

- MCP and HTTP are sibling adapters. The browser does not speak MCP stdio.
- HTTP handlers contain composition and serialization only; provider access
  remains behind services and capability routing.
- The HTTP server binds to loopback. Mobile or remote access is not enabled.
- Watchlist edits last for the current browser session only. Persistence is a
  separate service and storage concern for Milestone 6B.
- Strategy buttons are navigation affordances only in this milestone. They do
  not yet generate position legs or claim calculated results.
- The page uses system fonts and works without external web assets.

## HTTP contract

- `GET /api/v1/info`
- `GET /api/v1/providers`
- `GET /api/v1/workspaces/{symbol}` with optional `provider`, `expiration`,
  `put_call`, `strike_from`, `strike_to`, and bounded `limit` parameters.

Handled failures return an HTTP status plus the stable `error` object. Error
bodies do not include upstream payloads, tokens, or configuration secrets.

## Verification

- Python format and Ruff lint pass.
- Strict mypy passes across 44 source files.
- All 53 pytest tests pass, including four HTTP contract/CORS tests.
- `npm run build` passes TypeScript compilation and the Vite production build.
- A local request through the Vite `/api` proxy returned the combined fake SPY
  workspace successfully.

The in-app browser automation connection was unavailable during this milestone.
Open `http://127.0.0.1:5173` for the remaining visual inspection; this does not
affect the API or production-build verification.

## Next milestone

Milestone 6B adds SQLite-backed watchlist CRUD through a provider-neutral
watchlist service and HTTP endpoints, then replaces session-only UI state with
persistent server state.
