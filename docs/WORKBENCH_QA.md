# Workbench verification — 0.9.0

Validated on 2026-10-02, on macOS with Python 3.12 and Chromium. This record
describes automated and visual checks; it is not a claim that every market or
broker behavior is modeled.

## Core checks

| Check | Result |
| --- | --- |
| Ruff formatting and lint | Clean |
| Strict mypy | Clean, 66 source files |
| Python suite | 209 tests passed |
| TypeScript unit suite | 72 tests passed across 10 files |
| Chromium browser suite | 15 tests passed |
| React type checking and production build | Passed |
| Python source distribution and wheel | Built successfully |

Python regressions cover reference option prices, put/call parity, finite
difference Greeks, mark-to-IV inversion, calendar horizon handling, exact
payoff extrema and roots, multi-leg fees, signed credit accounting, assignment
disclosures, missing entry basis, provider valuation modes, risk sizing,
extreme/invalid inputs, tiny residual uncovered tails, and both HTTP and MCP
transports. Additional independent checks compared 200 generated portfolios
with a separately calculated terminal payoff grid and exercised 1,000 pricing
and IV round trips.

Browser tests exercise actual packaged assets against a local HTTP server:

- Editing entry prices/fees invalidates old results and changes payoff numbers.
- Calendar roadmaps stop at the first expiry and flag boundary Greeks.
- Custom roadmap dates, per-leg IV fitting and butterfly/short-put downside.
- Named setup and trade-plan persistence, backup/import and analysis briefs.
- Incomplete drafts preserve the saved library; saving retires stale Undo state.
- Failed analysis recovers; delayed responses cannot display results for newer
  inputs; blocked browser storage still permits analysis and export.
- Provider strategy transfer preserves the selected valuation and workspace.
- Delayed explorer draft restores use the latest valuation selection and are
  canceled when the user switches to another symbol.
- Both workspaces fit 1440, 768, 390 and 320 pixel viewports without document
  overflow. Wide financial tables scroll within their own panels.
- Workbench light/dark themes pass the axe WCAG 2 A/AA and 2.1 A/AA rules checked
  by the automated audit. Keyboard controls, visible field labels and chart
  slider are provided; this is not a complete assistive-technology audit.

Desktop and phone screenshots were inspected, including dark mode with 130%
text. The review caught and corrected tablet quote-panel overflow and cramped
mobile leg controls. The test runner regenerates screenshots in the ignored
`ui/test-results/` folder; the UI remains usable when horizontally scrolling
the option chain or scenario tables.

## Package smoke check

The built wheel was installed into an isolated temporary environment, reusing
existing dependency installations without importing application code from the
source checkout. All five console entry points resolved. The homepage and all
referenced JavaScript, CSS, theme, icon and manifest files served successfully.
An HTTP long-call example returned the expected $500 maximum loss; an actual
installed MCP stdio process returned a short put's $200 maximum profit and
$9,300 maximum loss. The wheel includes the provider contract helper and all
required static assets.

## Reproduce

```sh
uv sync --all-groups
make web-sync
make release-check
cd ui
npx playwright install chromium
npm run test:e2e
```

The browser configuration forces the synthetic provider and an isolated
temporary SQLite database. Tests do not need brokerage credentials. If browser
binaries are installed outside the default cache, set
`PLAYWRIGHT_BROWSERS_PATH` consistently for installation and execution.

In the implementation environment, `uv` is also available at the ignored
`.uv-bootstrap/bin/uv`. Restricted network access prevented one fresh build
cache from resolving Hatchling; the distribution build subsequently completed
using the established dependency cache. The constituent lint/type/test/build
checks above all completed successfully.

## Experimental branches

- `eshen/adjustment-lab`: explicit hold/close/adjust cash ledger, bounded numeric
  inputs and precision regressions; 130 relevant tests passed. HTML reports
  were inspected at 1440 and 390 pixels.
- `eshen/distribution-lab`: 36 new tests, 245 total branch tests passed, with
  lint/type checks clean. Checks include digital-like probability regions,
  deterministic cases, break-even plateaus, tail integration and model-label
  validation. Desktop and mobile report screenshots were inspected.

## Verification limits

Schwab OAuth and live responses were not exercised. No broker orders, American
exercise engine, assignment path, margin requirement, tax lot accounting or
historical option backtest is implemented. Current marks remain explicit user
inputs or copied provider snapshots. Cross-browser verification beyond Chromium
and a full screen-reader audit remain future work. Workbench storage is local
to one browser origin; the JSON backup is the portable copy.
