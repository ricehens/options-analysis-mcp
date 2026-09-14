# Project Status and Continuation Handoff

Last updated: 2026-09-14

## Current state

Milestone 6B persistent watchlists are complete on `codex/milestone-6b`. The
responsive React workspace now stores watchlist changes through a
provider-neutral service and private local SQLite database. The local FastAPI
and MCP interfaces continue to reuse the same application services and provider
routing. Live Schwab activation still requires the repository owner's local
developer credentials.

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
- [ ] Milestone 6C — Rich option-chain explorer
- [ ] Milestone 6D — Strategy builder and combined analytics
- [ ] Milestone 6E — Live Schwab UI verification and responsive hardening
- [ ] Milestone 7 — Optional streaming; decision gate not met

## Browser interface

- `GET /api/v1/info` returns safe local runtime metadata.
- `GET /api/v1/providers` returns enabled provider capabilities.
- `GET /api/v1/workspaces/{symbol}` combines the normalized quote, expiration
  list, and bounded filtered option chain.
- `make web-api` starts the loopback FastAPI service.
- `make web-ui` starts the Vite UI at `http://127.0.0.1:5173`.
- Watchlist changes persist through `/api/v1/watchlist` in a private local
  SQLite state file.

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

Milestone 6B pre-release checks pass: mypy strict reports no issues across 48
source files, all 59 tests pass, the React production build succeeds, and a
GET/POST/DELETE sequence through the Vite proxy persists to a temporary SQLite
database. Run the final `make release-check UV=.uv-bootstrap/bin/uv` before
tagging.

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
`STATUS.md`, `TODO.md`, and the latest milestone note. Inspect Git and the latest milestone
tag. Continue with Milestone 6C unless the owner requests live activation or a
different feature. Preserve the provider-neutral, local-only, read-only,
bounded, and secret-safe boundaries. Run `make release-check` and push a new
checkpoint. Never commit secrets or private responses.
