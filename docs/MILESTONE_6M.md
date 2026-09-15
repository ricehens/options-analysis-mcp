# Milestone 6M — Extensible Technical Indicators and Moving Averages

Completed: 2026-09-14

## Outcome

The underlying-price panel includes SMA 20 and SMA 50 overlays at every
supported resolution. Each overlay can be shown or hidden independently. A
period means one bar at the active resolution, and the chart explains that
relationship rather than implying a fixed number of days.

## Architecture

- Provider adapters continue to return canonical `PriceBar` values only.
- Pure calculators implement a small `TechnicalIndicatorCalculator` protocol.
- An explicit registry owns discovery by stable indicator ID; the execution
  service normalizes specifications, deduplicates requests, orders bars, and
  applies limits of eight indicators and 10,000 input bars.
- Definition and series models carry stable IDs, concrete specifications,
  parameters, source fields, chart roles, value units, and ordered Decimal
  points.
- HTTP exposes `/api/v1/technical-indicators` and repeated `indicator` query
  parameters on price history. MCP exposes `options_list_technical_indicators`
  and an optional `indicators` argument on `options_get_price_history`.
- The browser renderer consumes generic `price_overlay` series. It does not
  calculate SMA or inspect provider-specific data.

The API already reserves `lower_panel` and `event_markers` roles. Adding an EMA
or another price overlay requires a calculator, registry entry, metadata, and
tests. RSI/MACD will additionally need a lower-panel presentation component,
but still no provider change.

## Calculation and truncation decisions

SMA is the arithmetic mean of the previous N canonical closing prices,
including the current bar. It emits no partial warm-up values. Decimal
arithmetic is preserved through the backend boundary. The HTTP endpoint
calculates against the full provider response before filtering indicator points
to the visible, bounded bar set; hidden history can therefore provide valid
warm-up context without leaking extra bars.

## Safety and limitations

- Technical indicators are descriptive transforms, not trading advice or order
  signals.
- No execution, account mutation, new credential, or provider entitlement was
  added.
- SMA reflects the selected bar series and inherits its adjustments, session
  coverage, freshness, and provider quality limitations.
- Indicator selections are currently the curated SMA 20/50 controls and are not
  persisted. Catalog-driven selection is tracked as `TECH-040`.
- Visual owner confirmation remains separate under `UI-055A` because the
  browser-control runtime could not initialize during this milestone. Automated
  component and production-build checks passed, but no visual pass is claimed.

## Verification

Release verification and final counts are recorded in `STATUS.md`. Coverage
includes exact SMA arithmetic, input ordering, deduplication, bounds and invalid
specifications, HTTP and MCP discovery/results, generic SVG alignment,
accessible toggle state, theme token integrity, frontend production build, and
Python distributions.
