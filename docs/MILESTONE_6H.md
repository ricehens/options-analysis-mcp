# Milestone 6H — Warning and Provenance Details

Completed in code: 2026-09-14

## Delivered

- A reusable accessible warning-disclosure component.
- Underlying-quote warning details beside the quote timestamp.
- Chain-level warnings beside chain result metadata.
- Compact expandable warning controls for every call and put contract.
- Dedicated combined-analysis warnings, separate from analysis assumptions.
- Typed frontend contracts for `DataQualityWarning` and `FieldProvenance`.

## Information shown

Every disclosure retains the normalized warning code and human-readable
message. Affected field names are listed when supplied by the domain model. For
quote fields with provenance, the UI also displays source/provider, provenance
kind, and the source timestamp. Missing provenance remains visibly absent; it
is not inferred by the browser.

Examples include stale timestamps, missing or crossed markets, marks outside
the bid/ask range, missing open interest or implied volatility, incomplete
Greeks, multi-expiration payoff limitations, and incomplete cost basis.

## Interaction and safety

The controls use native `details`/`summary` disclosure semantics and explicit
screen-reader labels. Contract disclosures use compact count badges and open a
bounded overlay within the horizontally scrollable chain table. No warning is
suppressed because a contract is selected or a strategy is saved.

Warnings are informational quality signals, not trading recommendations. The
browser renders only normalized fields already returned by the local API and
does not receive provider payloads, credentials, or private account data.

## Verification

- Server-rendered React tests confirm that empty warnings render nothing.
- Detailed tests assert title, stable code, message, affected field, provider,
  provenance kind, and timestamp rendering.
- Compact-table tests assert disclosure styling and accessible count labels.
- All sixteen TypeScript tests and 70 Python tests pass.
- Strict typing across 55 source files, formatting, linting, the Vite build,
  and Python distribution builds pass through `make release-check`.

## Next decision gate

The scheduled browser feature backlog through `UI-052` is complete. Remaining
work requires either owner credentials (`LIVE-010`), a provider/data decision
(`DATA-010`), or a delivery decision (`MOB-010`). `TODO.md` remains the
canonical cross-session queue.
