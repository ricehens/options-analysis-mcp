# Changelog

## 0.6.5 — 2026-09-14

- Expanded the provider-neutral catalog from eight to fifteen templates with
  protective puts, collars, cash-secured puts, straddles, strangles, call
  calendars, and call diagonals.
- Added explicit expiration-order metadata and a volatile strategy outlook.
- Added automatic next-expiration loading for calendar and diagonal drafts
  without provider-specific frontend logic.
- Added hand-calculated payoff fixtures for protective puts, collars,
  cash-secured puts, straddles, and strangles plus multi-date draft tests.

## 0.6.4 — 2026-09-14

- Bundled the production React assets into the Python distribution so one
  loopback FastAPI process serves both the browser workspace and API.
- Added same-origin content security, no-referrer, MIME-sniffing, and framing
  protections plus API coverage for static delivery and headers.
- Improved keyboard semantics, visible focus, screen-reader status text, touch
  targets, narrow-screen controls, and reduced-motion behavior.
- Added a minimal local web-app manifest and durable Milestone 6E handoff.

## 0.6.3 — 2026-09-14

- Added a provider-neutral catalog for long calls/puts, covered calls, bullish
  and bearish verticals, long call butterflies, iron condors, and custom legs.
- Added a read-only HTTP position-analysis endpoint over the existing service.
- Added one-click template-to-leg generation, editable action/quantity/entry
  values, combined debit/credit and Greeks, payoff chart, break-evens, bounded
  risk, scenario table, assumptions, and warnings.
- Expanded deterministic option pricing and added hand-calculated iron-condor,
  template-generation, signed-leg, and payoff-chart tests.

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
