# Milestone 6G — Persistent Named Strategy Drafts

Completed in code: 2026-09-14

## Delivered

- Provider-neutral `StrategyDraft`, `StrategyDraftDefinition`, and
  `StrategyDraftLeg` domain contracts.
- A storage-independent `StrategyDraftService` and repository protocol.
- A SQLite adapter with a dedicated `strategy_drafts` table in the existing
  private local state database.
- `GET`, `POST`, and `DELETE /api/v1/strategy-drafts` contracts.
- Browser controls to name, save, update, reopen, and delete research setups.
- Fresh quote rehydration through the existing position-analysis service when
  opening a saved draft.

## Persistence contract

Draft names are unique without regard to case. Saving the same name updates the
definition while preserving its UUID and creation timestamp. Each definition
stores the canonical and provider symbols, provider ID, underlying, template
ID, signed quantities, asset types, and entry prices. It does not store quote
snapshots, account identifiers, credentials, tokens, or order instructions.

Provider identity is explicit because option lookup symbols can differ by
vendor. The schema remains provider-neutral, and its canonical symbol is
retained for a future migration workflow, but reopening currently requires the
saved provider to be enabled and authorized.

The SQLite adapter creates its table independently of the watchlist adapter,
uses bound SQL parameters and an immediate transaction for upserts, and retains
the existing user-only file permissions.

## Rehydration behavior

Opening a draft sends its signed legs through `PositionAnalysisService`. The
service resolves current quotes, enforces one provider, and returns normalized
instruments. The browser reconstructs editable buy/sell legs from that result
and preserves the saved entry prices. Provider errors, missing symbols, and
reauthorization requirements remain visible rather than falling back to stale
data.

## Verification

- SQLite tests cover first save, case-insensitive update, stable identity,
  restart persistence, private file mode, and idempotent deletion.
- Domain tests reject empty definitions and zero-quantity legs.
- HTTP tests cover empty list, create, update, list, and delete.
- TypeScript tests cover signed serialization and editable-leg reconstruction
  from enriched analysis.
- All 70 Python tests and thirteen TypeScript tests pass.
- Strict typing across 55 source files, formatting, linting, the Vite build,
  and Python distribution builds pass through `make release-check`.
- An isolated install of the built `0.6.6` wheel served the packaged UI and
  successfully saved and listed a two-leg named draft through the HTTP API.

## Next work

`UI-052` in `TODO.md` adds expandable per-contract and per-analysis warning
details. Owner-driven live Schwab activation remains independently blocked on
local credentials.
