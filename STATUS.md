# Project Status and Continuation Handoff

Last updated: 2026-09-14

## Current state

Milestone 6G saved strategies are complete on `codex/milestone-6g`. Named
strategy drafts persist in a dedicated table in the local state database,
remain separate from watchlists and provider adapters, and reopen through fresh
provider quote enrichment. Saving the same case-insensitive name updates its
stable draft ID. FastAPI and MCP continue to reuse the same provider-neutral
services and routing. Live Schwab activation still requires owner credentials.

Repository: https://github.com/xuemingshen-oracle/options-analysis-mcp

The canonical cross-session work queue is `TODO.md`. Update it with every
milestone; do not rely on chat history as the backlog.

## Milestone checklist

- [x] Milestone 0 — Design and handoff documentation
- [x] Milestone 1 — Offline project skeleton
- [x] Milestone 2 — OAuth and Schwab read-only gateway (offline code)
- [ ] Milestone 2 operational activation — owner OAuth and one live read
- [x] Milestone 3 — Option market-data tools (offline code)
- [ ] Milestone 3 operational activation — owner live mapping check
- [x] Milestone 4 — Caller-supplied position enrichment and analytics
- [ ] Optional Schwab account positions — requires Trader API entitlement
- [x] Milestone 5 — Hardening, documentation, and packaging
- [x] Milestone 6A — FastAPI and responsive React browser foundation
- [x] Milestone 6B — SQLite-backed persistent watchlists
- [x] Milestone 6C — Rich option-chain explorer
- [x] Milestone 6D — Strategy builder and combined analytics
- [x] Milestone 6E — Packaged browser delivery and responsive hardening
- [x] Milestone 6F — Expanded strategy catalog and multi-expiration workflows
- [x] Milestone 6G — Persistent named strategy drafts
- [ ] Milestone 7 — Optional streaming; decision gate not met

## Browser interface

- `GET /api/v1/info` returns safe local runtime metadata.
- `GET /api/v1/providers` returns enabled provider capabilities.
- `GET /api/v1/workspaces/{symbol}` combines the normalized quote, expiration
  list, and bounded filtered option chain.
- `make web-api` serves the bundled UI and API at `http://127.0.0.1:8000`.
- `make web-ui` starts the development-only Vite UI at
  `http://127.0.0.1:5173`.
- Watchlist changes persist through `/api/v1/watchlist` in a private local
  SQLite state file.
- The chain explorer displays paired calls/puts with provider-side strike
  bounds, local liquidity/moneyness filters, sortable detailed metrics, and a
  selected-contract draft tray.
- The HTTP strategy catalog and position-analysis endpoint support fifteen
  presets/custom legs without adding any order capability.
- Call calendars and diagonals fetch the next available expiration through the
  same normalized workspace endpoint; no provider-specific UI logic is added.
- Named strategy definitions support list, save/update, rehydrate, and delete
  operations through `/api/v1/strategy-drafts`.
- Production assets are packaged under `options_analysis.web.static`, use
  same-origin API calls, and receive a restrictive content security policy.

## Available MCP tools

- `options_server_info`
- `options_list_providers`
- `options_provider_auth_status`
- `options_get_underlying_quote`
- `options_get_option_expirations`
- `options_get_option_chain`
- `options_get_option_quotes`
- `options_get_price_history`
- `options_analyze_positions`

Every tool result now includes `error`; it is null on success and contains a
stable, secret-safe detail object for handled failures.

## Hardening delivered

- GET-only Schwab gateway, exact OAuth callback/state validation, private atomic
  token storage, bounded timeouts/retries/response bytes, and no redirect follow.
- Provider-normalized values, provenance, quality warnings, and sanitized schema
  drift paths.
- Bounded one-second LRU/TTL cache for repeated underlying quotes only.
- Packaged `options_analysis.testing.assert_market_data_provider_contract`.
- Operations, security, MCP-host, provider, release, milestone, and changelog
  documentation.
- `make release-check` performs formatting, lint, strict typing, tests, and
  package builds.

## Verification evidence

Milestone 6G pre-release checks pass: mypy strict reports no issues across 55
source files, all 70 Python tests and thirteen TypeScript tests pass, and the
React production bundle and Python distributions build successfully. Detailed
persistence and runtime evidence is recorded in `docs/MILESTONE_6G.md`.

## Required owner activation

1. Follow `docs/MILESTONE_2.md` and `docs/OPERATIONS.md` for local OAuth.
2. Confirm current official endpoints and the mapping assumptions in
   `docs/MILESTONE_3.md`.
3. Run one narrow live stock quote, expiration list, chain, selected option
   quote, and position analysis without saving provider bodies.
4. Decide whether Trader API Individual is available and whether account
   positions are worth adding.

Never paste or commit credentials, callbacks, token values, account data, or
captured live responses.

## Streaming decision gate

Milestone 7 is deliberately optional. Do not implement it until live use shows
that snapshot latency is inadequate. If needed, implement the existing
`StreamingProvider` contract with bounded symbol subscriptions, bounded cache,
freshness timestamps, reconnect/resubscribe tests, and no order functionality.

## Resume prompt for another session

Continue the provider-pluggable options-analysis project at
`/Users/xuemingshen/Workspaces/schwab`. Read `README.md`, `SECURITY.md`,
`STATUS.md`, `TODO.md`, and the latest milestone note. Inspect Git and the latest
milestone tag. Take the lowest-numbered `ready` item in `TODO.md`, or ask the
owner to choose among backlog items if none is ready. Preserve the
provider-neutral, local-only, read-only, bounded, and secret-safe boundaries.
Run `make release-check` and push a new checkpoint. Never commit secrets or
private responses.
