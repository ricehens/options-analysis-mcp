# Changelog

## 0.6.2 — 2026-09-14

- Added provider-side strike bounds and local moneyness, open-interest, and
  bid/ask spread filters to the option-chain explorer.
- Added sortable strike, IV, and open-interest columns with delta, liquidity,
  freshness, and data-quality visibility.
- Added contract selection into editable buy/sell draft legs.
- Added Vitest coverage for chain pairing, filtering, sorting, spread, and DTE
  calculations; frontend tests now run in the release check.

## 0.6.1 — 2026-09-14

- Added a provider-neutral watchlist service and SQLite persistence adapter.
- Added idempotent list/add/remove HTTP endpoints and connected the React
  controls to server-side persistence.
- Added first-run defaults, explicit empty-list preservation, symbol
  validation, private database permissions, and restart-safe tests.

## 0.6.0 — 2026-09-14

- Added a local-only FastAPI interface beside MCP using the same application
  services and provider routing.
- Added a responsive React/TypeScript/Vite research workspace with an editable
  in-memory watchlist, quote summary, expiration filters, and option-chain view.
- Added transport-neutral structured errors shared by MCP and HTTP.
- Added HTTP contract tests and frontend production-build verification.

## 0.5.0 — 2026-09-14

- Added stable structured MCP error details and sanitized schema paths.
- Added a bounded process-local TTL cache for repeated underlying snapshots.
- Packaged the provider conformance helper for external adapter authors.
- Added operating, security, MCP-host, provider, and release guides.

## 0.4.0 — 2026-09-14

- Added caller-supplied position enrichment and first option analytics.

## 0.3.0 — 2026-09-14

- Added normalized market-data tools and Schwab response mapping.

## 0.2.0 — 2026-09-14

- Added Schwab OAuth, token storage, read-only gateway, and auth status.

## 0.1.0 — 2026-09-14

- Added the provider-pluggable offline skeleton and fake provider.
