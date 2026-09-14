# Durable Project Backlog

Last updated: 2026-09-14

This file is the canonical cross-session task list. `STATUS.md` describes the
current checkpoint; this file records what remains and the order in which to do
it. Every milestone must update both files before commit.

## Workflow

Statuses are `in_progress`, `ready`, `blocked`, `backlog`, `deferred`, and
`done`. A new session should:

1. Read `STATUS.md`, this file, and the latest milestone note.
2. Finish the sole `in_progress` item, if present.
3. Otherwise take the lowest-numbered `ready` item whose dependencies are done.
4. Add verification evidence and update status before committing.
5. Keep stable IDs when tasks are refined; add child IDs instead of replacing
   history.

## Active sequence

| ID | Status | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- | --- |
| UI-010 | done | Milestone 6B: SQLite-backed watchlist service, CRUD API, and persistent React controls | UI-001 code | CRUD/restart tests, proxy CRUD check, release check |
| UI-011 | blocked | Manually inspect the responsive Milestone 6A–6C UI in a browser and record defects | Browser-control availability or owner inspection | Desktop and narrow viewport screenshots or inspection notes |
| UI-020 | done | Milestone 6C: chain explorer with strike range, expiration/DTE, side, liquidity, and moneyness filters | UI-010 | API filter and TypeScript view-model tests |
| UI-021 | done | Add sortable chain columns and clear stale/missing-data indicators | UI-020 | Sort tests and visible freshness/warning summary |
| UI-022 | done | Add contract selection from calls/puts into a draft leg tray | UI-020 | Buy/sell/quantity/remove UI with production build |
| UI-030 | done | Milestone 6D: canonical strategy-template catalog | UI-022 | Catalog and template-generation tests |
| UI-031 | done | Add editable signed legs for long call/put, covered call, verticals, butterflies, and iron condors | UI-030 | Hand-calculated iron-condor and signed-leg tests |
| UI-032 | done | Add combined debit/credit, Greeks, max profit/loss, and break-even results | UI-031 | Service/API tests and runtime proxy result |
| UI-033 | done | Add expiration payoff chart and scenario table with assumptions/warnings | UI-032 | Payoff geometry tests and production build |
| UI-040 | done | Milestone 6E: responsive/accessibility hardening and production static serving/packaging | UI-033 | Semantic/focus/reduced-motion tests by build, API static/header test, one-process startup, wheel inspection |
| UI-050 | done | Milestone 6F: expand catalog with protective put, collar, cash-secured put, straddle/strangle, and calendar/diagonal workflows | UI-040 | Fifteen catalog definitions, automatic second-expiration loading, draft/payoff fixtures |
| UI-051 | backlog | Persist named strategy drafts separately from watchlists | UI-040 | SQLite migration and restart CRUD tests |
| UI-052 | backlog | Add expandable per-contract and analysis warning details | UI-040 | Warning rendering tests |

## Schwab activation

These require the repository owner’s approved application and private local
credentials. Never put evidence containing tokens or private provider bodies in
Git or chat.

| ID | Status | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- | --- |
| LIVE-010 | blocked | Complete local Schwab OAuth authorization | Owner credentials/application | Safe auth-status summary only |
| LIVE-020 | blocked | Verify one stock quote, expirations, narrow chain, and selected option quotes | LIVE-010 | Shape/mapping checklist without response bodies |
| LIVE-030 | blocked | Run the browser workspace against Schwab and check freshness/rate behavior | LIVE-020, UI-020 | Redacted inspection notes |
| LIVE-040 | deferred | Evaluate read-only Trader API account positions | Trader API entitlement | Explicit go/no-go decision |

## Provider portability and richer data

| ID | Status | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- | --- |
| DATA-010 | backlog | Select the second provider based on live vs historical needs; initial candidates are Tradier, Alpaca, Massive, ORATS, and Databento | LIVE-020 | Short decision record with current official API evidence |
| DATA-020 | backlog | Implement the selected provider through existing capability contracts | DATA-010 | Shared conformance suite passes without core-analysis changes |
| DATA-030 | backlog | Define snapshot provenance/synchronization rules if positions and quotes use different providers | DATA-020 | Mixed-source domain and warning tests |

## Backtesting and research

| ID | Status | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- | --- |
| BT-010 | backlog | Define backtest questions, strategy universe, fill model, and required historical fields | UI-033, DATA-010 | Backtest design decision record |
| BT-020 | backlog | Choose/licence historical option data with survivorship, corporate-action, quote, and timestamp coverage | BT-010 | Vendor/dataset validation report |
| BT-030 | backlog | Add immutable snapshot storage and versioned dataset schema | BT-020 | Reproducible import and integrity tests |
| BT-040 | backlog | Implement fills, slippage, assignment/exercise, expiration, dividends, fees, and early-close rules | BT-030 | Synthetic deterministic backtests |
| BT-050 | backlog | Add walk-forward reporting and guardrails against look-ahead/selection bias | BT-040 | Bias tests and reproducible report |

## Delivery and optional extensions

| ID | Status | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- | --- |
| MOB-010 | backlog | Decide local desktop wrapper versus authenticated hosted/PWA mobile delivery | UI-040 | Deployment/security decision record |
| MOB-020 | backlog | Add TLS, authentication, host/origin controls, and deployment isolation before any LAN/mobile exposure | MOB-010 | Threat-model review and integration tests |
| STREAM-010 | deferred | Measure snapshot latency and decide whether streaming is justified | LIVE-030 | Recorded latency and go/no-go threshold |
| STREAM-020 | deferred | Implement bounded streaming adapter/cache only if STREAM-010 says go | STREAM-010 | Reconnect, resubscribe, freshness, and memory-bound tests |
| EXEC-010 | deferred | Reconsider trading/order execution as a separate project and threat model | Explicit owner request | New design approval; never implicit in a data-provider plug-in |

## Completed checkpoints

| ID | Status | Result |
| --- | --- | --- |
| CORE-000 | done | Design and cross-session handoff documentation |
| CORE-010 | done | Provider-pluggable offline skeleton and fake adapter |
| CORE-020 | done | Schwab OAuth and bounded read-only gateway code |
| CORE-030 | done | Normalized option market-data tools and adapter mapping |
| CORE-040 | done | Caller-supplied position enrichment and analytics |
| CORE-050 | done | Error/cache/security/packaging hardening |
| UI-001 | done | Milestone 6A FastAPI and responsive React browser foundation |
