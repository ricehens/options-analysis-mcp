# Milestone 6I — Adjustable Interface Typography

Completed: 2026-09-14

## Outcome

The browser workspace now offers four bounded text-size settings: 90%, 100%,
115%, and 130%. Controls live at the bottom of the desktop sidebar and below
the watchlist on narrow screens. The percentage button resets the interface to
100%.

The preference is presentation-only. It is saved under
`option-atlas.font-scale` in browser-local storage and is never sent to the
local API or a market-data provider. If storage is unavailable, adjustment
continues to work for the current page session.

## Design decisions

- Existing pixel-based typography was converted to root-relative units, so
  the setting changes text without indiscriminately scaling layout geometry.
- Native browser zoom remains available and composes with the app preference.
- Mobile form fields retain a 16-pixel minimum to avoid unintended input zoom.
- The controls use native buttons, a labelled group, visible focus styling,
  disabled bounds, and a dynamic accessible reset label.
- This is a provider-neutral UI preference and adds no Schwab-specific code,
  credentials, network calls, or order capability.

## Verification

- `npm test`: 19 tests in 5 files pass, including normalization, bounds, and
  browser-storage behavior.
- `npm run build`: TypeScript compilation and the Vite production build pass.
- `make release-check`: formatting, lint, strict typing across 55 source files,
  70 Python tests, 19 TypeScript tests, the React bundle, and both Python
  distributions pass.

The owner approved the desktop layout before this addition. Narrow-viewport
manual inspection remains tracked as `UI-011`; the responsive placement is
covered by the existing CSS breakpoint.

## Next milestone

`UI-054` / Milestone 6J adds a provider-neutral underlying price chart with
1-minute, 5-minute, daily, weekly, and monthly views.
