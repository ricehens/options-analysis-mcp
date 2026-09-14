# Milestone 4 — Position Enrichment and First Analytics

Completed in code: 2026-09-14

## Delivered

- `options_analyze_positions`, a provider-neutral MCP tool accepting 1–100
  signed caller-supplied equity, ETF, or option legs.
- Quote enrichment through the existing market-data service and selected
  provider; analytics never imports a concrete adapter.
- Mark, midpoint, and liquidation valuation modes. Liquidation uses bid for a
  long leg and ask for a short leg, with explicit fallback behavior.
- Per-leg current value, signed cost basis, and unrealized profit/loss.
- Contract-multiplier-aware aggregate delta, gamma, theta, vega, and rho.
- Completeness metadata and missing-symbol lists for every Greek.
- Exact piecewise-linear expiration payoff for one-underlying, one-expiration
  positions, including equity legs.
- Break-even roots and bounded/unbounded maximum profit and minimum P/L.
- A bounded delta-gamma underlying-price scenario grid.
- Explicit assumptions and warnings for missing prices/costs/Greeks,
  inconsistent underlying snapshots, multiple underlyings, and calendars.

## Input and sign conventions

- Positive quantity is long; negative quantity is short.
- `average_open_price` is per share or per option underlying unit.
- Equity and ETF multiplier is 1; each option uses its mapped contract
  multiplier, normally 100.
- Cost basis retains position sign. A short option opened for a credit therefore
  has negative cost basis.
- `max_loss` is the minimum attainable profit/loss number. It is negative for a
  conventional loss. When loss is unbounded, the value is null and
  `max_loss_bounded` is false.

## Analysis limits

- Exact payoff is omitted for multiple underlyings or multiple option
  expirations because later-expiring options retain unknown time value.
- Break-even and risk bounds require an open price for every leg.
- Current scenarios use provider delta and gamma only; volatility and time are
  fixed, and cross-Greek effects are not modeled.
- Provider-supplied Greeks retain provider provenance and are not an independent
  risk model.
- Scenario moves must be greater than -100%, no more than +500%, and contain at
  most 21 points.

## Optional account positions

Schwab account retrieval is not enabled because Trader API entitlement has not
been established. This is an optional design deliverable, not a prerequisite
for caller-supplied analysis. A later implementation must use the read-only
`PortfolioProvider` capability, mask account identifiers, and remain separately
feature-gated. No order endpoint or execution contract exists.

## Verification

Hand-calculated tests cover a vertical call spread, a long call, a naked short
call, liquidation-side pricing, missing cost basis, calendar suppression,
scenario bounds, zero bids, and multiple underlyings. The real MCP protocol test
calls the analysis tool and checks the vertical's $200 maximum profit and $98
break-even.
