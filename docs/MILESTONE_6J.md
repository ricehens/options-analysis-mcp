# Milestone 6J — Underlying Price History Chart

Completed: 2026-09-14

## Outcome

The browser workspace now includes a dedicated underlying-price panel between
the quote summary and option workflow. Five keyboard-operable interval controls
select one-minute, five-minute, daily, weekly, or monthly bars. The chart shows
closing prices, range, net change, time bounds, provider, and bar count, with
explicit loading, empty, and error states.

## Provider-neutral contract

`GET /api/v1/price-history/{symbol}` accepts an optional provider, one supported
resolution, and an optional aware end timestamp. The server selects a bounded
lookback window and calls the existing `HistoricalDataProvider` through
`MarketDataService`; the browser contains no Schwab response mapping.

| Resolution | Default lookback | UI label |
| --- | ---: | --- |
| `1m` | 1 day | `1m` |
| `5m` | 7 days | `5m` |
| `1d` | 365 days | `1D` |
| `1w` | 5 years | `1W` |
| `1mo` | 20 years | `1M` |

Responses are sorted oldest to newest and capped at the latest 500 bars, with a
`truncated` flag. The existing Schwab adapter already maps all five resolutions
to its price-history gateway; the deterministic fake adapter now supplies
multi-bar offline series for the same contract.

## Chart behavior

- A React-native SVG line and subtle area encode closing price; high/low values
  determine the plotted vertical range so the close line is never clipped.
- Direct axis and range labels make the single series understandable without a
  legend or color-only meaning.
- The SVG has a generated accessible title and description. Interval controls
  use native buttons with `aria-pressed` and full interval/lookback labels.
- Symbol or interval changes abort stale requests and clear the previous series
  before rendering a new symbol label.
- No external chart package, font, analytics service, credential, or order
  capability was added.

## Schwab portal activation

The owner began registering a production app with **Market Data Production**,
an order limit of zero, and callback `https://127.0.0.1`. The root callback
validator now treats empty and slash root paths as equivalent because browsers
may display the slash, while scheme, authority, non-root path, fragment, and
OAuth state remain strictly checked. App keys and secrets stay only in the
ignored local `.env` and must never be pasted into chat or committed.

## Verification

- Focused Python tests cover all five resolutions, normalized ordered bars,
  bounded response metadata, invalid intervals, and callback validation.
- TypeScript tests cover the interval catalog, chart geometry, flat/empty
  series, net change, and accessible server rendering.
- The production bundle loads the history endpoint successfully with the fake
  provider at `http://127.0.0.1:8000`.
- `make release-check` passes formatting, lint, strict typing across 55 source
  files, 76 Python tests, 23 TypeScript tests, the React production bundle, and
  both Python distributions.

## Remaining work

- `LIVE-010` through `LIVE-030`: wait for portal approval, perform local OAuth,
  verify live mappings without saving provider bodies, and inspect the browser
  against Schwab.
- `UI-011`: manually inspect the narrow-viewport layout when browser-control
  support is available or the owner can provide a mobile screenshot.
