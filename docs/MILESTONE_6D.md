# Milestone 6D — Strategy Builder and Combined Analysis

Completed in code: 2026-09-14

## Delivered

- A canonical provider-neutral strategy catalog with stable identifiers and
  typed leg-role metadata.
- Templates for long call, long put, covered call, bull call spread, bear put
  spread, long call butterfly, iron condor, and custom legs.
- `GET /api/v1/strategies` and read-only
  `POST /api/v1/analyses/positions` HTTP contracts.
- One-click template generation from the currently loaded normalized chain.
- Editable buy/sell action, quantity, and entry price for every draft leg.
- Automatic conversion to signed analysis quantities and enrichment with fresh
  provider quotes through the existing `PositionAnalysisService`.
- Combined entry debit/credit, max profit/loss with boundedness, break-evens,
  aggregate delta/gamma/theta/vega, expiration payoff SVG, delta-gamma scenario
  table, assumptions, and warnings.

## Template strike rules

- Single calls/puts select the strike nearest spot.
- Covered calls use 100 shares and the first call at or above spot.
- Bull call and bear put spreads use adjacent strikes around spot.
- Long call butterflies use three consecutive call strikes centered near spot.
- Iron condors use the two nearest loaded puts below spot and calls above spot.
- Custom mode retains manually selected contracts.

If filters omit required strikes or sides, template construction fails with a
specific instruction to widen the loaded chain. It does not silently invent a
contract.

## Analysis semantics

- Entry prices default to normalized current marks, then midpoint or last, and
  are explicitly editable.
- Positive quantities are buys/long; negative quantities are sells/short.
- Option premiums and Greeks are multiplied by contract multiplier and signed
  quantity.
- Positive net cost basis is labeled debit; negative is labeled credit.
- Exact expiration payoff requires one underlying and at most one option
  expiration. Calendarized drafts retain warnings and omit that chart.
- Scenarios are delta-gamma approximations with volatility and time held fixed;
  they are not forecasts.

## Safety boundary

Templates are research presets, not recommendations. The endpoint enriches and
analyzes caller-supplied legs but cannot preview, route, place, replace, or
cancel an order. Provider credentials and tokens remain server-side.

## Verification

- 62 Python tests include the catalog/API contract and a hand-calculated iron
  condor with a $300 credit, $300 bounded maximum profit, $200 bounded maximum
  loss, and $92/$108 break-evens.
- Nine TypeScript tests cover chain behavior, template-to-leg generation,
  signed quantity conversion, expected vertical/butterfly/condor strikes, and
  payoff SVG geometry.
- A runtime request through the Vite proxy returned all eight templates and the
  expected iron-condor combined analysis with eight payoff points.
- `make release-check` covers Python format/lint/type/tests, TypeScript tests,
  React production build, and Python source/wheel builds.

## Next milestone

Milestone 6E (`UI-040`) packages the built frontend with the local API and adds
responsive/accessibility hardening. Owner-driven Schwab activation remains
tracked independently as `LIVE-010` through `LIVE-030` in `TODO.md`.
