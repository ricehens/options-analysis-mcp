# Milestone 6F — Expanded Strategy Catalog

Completed in code: 2026-09-14

## Delivered

The provider-neutral catalog now exposes fifteen templates:

- long call and long put;
- covered call, protective put, collar, and cash-secured put;
- bull call spread and bear put spread;
- long straddle and long strangle;
- long call butterfly and iron condor;
- call calendar and call diagonal; and
- custom legs.

`StrategyLegRole` now records optional expiration order as well as strike order,
and the outlook vocabulary includes `volatile`. These fields describe strategy
shape without containing provider symbols or order-routing instructions.

## Template construction

- Protective puts use 100 shares and the nearest loaded put at or below spot.
- Collars use 100 shares, the nearest put below spot, and the nearest call above
  spot.
- Cash-secured puts sell the nearest loaded put below spot. Cash collateral is
  an external funding requirement, not a synthetic analysis leg.
- Straddles use matching near-money call and put strikes.
- Strangles use the nearest loaded put below and call above spot.
- Call calendars sell the near-date at-the-money call and buy the same strike
  in the next available expiration.
- Call diagonals sell the nearest higher-strike near-date call and buy a
  near-money call in the next available expiration.

The browser determines multi-date needs from catalog expiration-order metadata
and requests the next chain through the existing provider-neutral workspace
API. Missing strikes, missing later dates, different providers, and different
underlyings fail visibly instead of producing partial strategies.

## Analysis semantics

Single-expiration strategies receive exact piecewise-linear expiration payoff,
break-even, and bounded-risk analysis. Calendar and diagonal drafts aggregate
current market value and provider Greeks, but deliberately omit exact
expiration payoff because their legs expire on different dates. The existing
`multiple_expirations` warning explains that limitation.

The presets remain research conveniences, not recommendations, collateral
calculators, order previews, or execution instructions.

## Verification

- Catalog/API tests assert fifteen stable templates and calendar expiration
  roles.
- TypeScript tests verify every new template's selected strikes, actions,
  quantities, dates, and later-expiration selection.
- Hand-calculated analytics fixtures cover protective-put and collar bounds,
  cash-secured-put risk, and straddle/strangle break-evens.
- All 66 Python tests and twelve TypeScript tests pass.
- Strict typing, formatting, linting, the Vite build, and Python package builds
  pass through `make release-check`.
- An isolated install of the built wheel returned all fifteen templates, a
  five-contract next-expiration call chain, and a calendar analysis with the
  expected `multiple_expirations` warning and no misleading payoff curve.

## Next work

`UI-051` in `TODO.md` adds persistent named strategy drafts without coupling
watchlist storage to providers or trading execution.
