# Milestone 6C — Option-Chain Explorer

Completed in code: 2026-09-14

## Delivered

- Expiration and call/put selection with DTE labels.
- Provider-side lower/upper strike bounds sent through the normalized workspace
  endpoint.
- Local near-money, minimum-open-interest, and maximum-spread filters.
- Paired call/put rows with delta, implied volatility, bid, ask, bid/ask spread,
  open interest, strike, and percentage distance from spot.
- Sortable strike, call/put IV, and call/put open-interest columns.
- Provider freshness and aggregate normalized quality-warning status.
- Contract selection into a draft tray with buy/sell action, quantity, remove,
  and clear controls.
- Pure TypeScript view-model tests run as part of `make release-check`.

## Boundary and calculation decisions

- Strike bounds are provider request parameters. Moneyness and liquidity are
  deterministic presentation filters over the returned normalized quotes.
- When only one side at a strike passes liquidity filters, the failing side is
  hidden rather than implying it also passed.
- Spread percentage is `(ask - bid) / midpoint * 100`. Crossed, missing, or
  zero-midpoint markets have no usable spread and fail a maximum-spread filter.
- Moneyness filtering means absolute percentage distance between strike and
  current underlying mark. Directional ITM/OTM labels are deferred because they
  differ for calls and puts in a paired row.
- Missing sort values remain last so incomplete contracts do not appear best.
- The draft tray is deliberately not position analysis. Selecting a contract
  cannot place, preview, or submit an order.

## Known limits

- The workspace request remains bounded to 100 contracts. Local filters do not
  cause automatic provider pagination; use strike/date bounds to narrow the
  server request first.
- Draft legs are currently browser-session state and are cleared when the
  underlying changes.
- Quality status is summarized by count; expandable warning details belong in
  a later polish task.
- Strategy templates do not yet generate or analyze legs.

## Verification

- Four Vitest cases cover call/put pairing, per-side liquidity filtering,
  moneyness, spread calculation, missing-value sorting, and UTC DTE.
- The FastAPI workspace test covers exact strike-range propagation.
- Python checks, frontend tests/build, and Python package builds all run under
  `make release-check`.

## Next milestone

Milestone 6D begins with `UI-030` in `TODO.md`: a canonical strategy-template
catalog that generates validated signed position legs, followed by combined
analytics and payoff visualization.
