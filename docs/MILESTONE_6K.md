# Milestone 6K — Validated Snapshot Replay

Completed: 2026-09-14

## Outcome

The entire analysis stack can now run against a versioned local dataset without
a broker login, network request, or provider-specific UI path. The `replay`
adapter implements the same quote, expiration, chain, selected-contract, and
underlying-history contracts as live market-data providers.

## Data and licensing decision

An exploratory delayed SPY request confirmed that current public option data has
the fields needed by the canonical models. The associated Cboe delayed-quote
page explicitly prohibits automated extraction, so that response was deleted,
no endpoint adapter was added, and no vendor data is stored in this repository.
The replay milestone uses locally generated synthetic data only.

Reference: [Cboe delayed quotes](https://www.cboe.com/delayed_quotes/spy/quote_table/)

## Bundle boundary

- `schema_version: 1` makes future migrations explicit.
- Source label, original provider ID, acquisition time, and usage notes make
  provenance auditable.
- Nested canonical models retain Decimal values, aware timestamps, warnings,
  field provenance, Greeks, instrument identity, and namespaced extensions.
- Symbols, contract provider symbols, and history resolutions must be unique;
  history bars must be ordered oldest to newest.
- Loading is bounded to 25 MB by default and rejects absent, oversized,
  unreadable, or schema-invalid files before serving data.
- Returned models use provider ID `replay`; the original quote provider remains
  available in provenance and `replay.original_provider_id`.
- The provider filters dates, put/call, strikes, limits, resolutions, and time
  windows locally without changing application services.

## Safe sample workflow

`options-analysis-replay-sample` atomically creates a user-only synthetic file
with SPY quotes, two expirations, calls/puts, Greeks, liquidity, and 1m, 5m, 1d,
1w, and 1mo history. It contains no downloaded, account, or credential data.

Real captures are deliberately not automated. Before any future exporter is
added, its source must explicitly permit local recording, and the workflow must
sanitize identifiers and keep captures outside Git.

## Verification

- The shared market-data conformance suite passes for `ReplayProvider`.
- Focused tests cover configuration state, strict file loading, size limits,
  origin retention, chain filters, and bounded history windows.
- The synthetic CLI bundle loads through application composition and serves the
  existing browser/API workflow with no core analysis or frontend change.
- A local HTTP smoke check returned `replay` ready, 20 SPY option contracts, 252
  daily bars, and null errors for provider, workspace, and history responses.
- Full release-check evidence is recorded in `STATUS.md`.

## Next milestone

Milestone 6L adds persistent light, dark, and system-selected visual themes over
semantic color tokens, as requested by the owner.
