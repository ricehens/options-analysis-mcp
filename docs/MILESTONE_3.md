# Milestone 3 — Option Market Data

Completed in code: 2026-09-14

## Delivered

- Provider-neutral application-service operations for stock quotes, option
  expirations, filtered chains, selected option quotes, and price history.
- Five matching generic MCP tools. Schwab never appears in a tool name or core
  result field.
- Schwab source models that ignore unknown vendor fields while validating every
  field used by canonical mapping.
- Canonical instrument identity, `Decimal` values, timezone-aware timestamps,
  field provenance, namespaced provider extensions, and option terms.
- Quality warnings for missing/stale timestamps, missing or crossed markets,
  marks outside the market, missing open interest/IV/Greeks, partial Greeks,
  partial chain rows, and empty chains.
- Locally enforced chain filters and a 100-contract MCP maximum.
- A default 45-day Schwab expiration window and bounded upstream response size.
- Translation of underlying-history resolutions into Schwab frequency fields.
- Synthetic fixtures covering equity and option quotes, expirations, full and
  partial chains, empty chains, history, and schema failures.
- The same shared market-data conformance test now passes for fake and Schwab
  adapters.

## Mapping decisions to verify live

The adapter currently maps Schwab's `volatility` percentage points to a
canonical ratio by dividing by 100. Settlement codes `P` and `C` map to
physical and cash, and exercise codes `A` and `E` map to American and European.
These assumptions and the configured paths `/quotes`, `/expirationchain`,
`/chains`, and `/pricehistory` must be checked against the current official
portal during owner activation. All are isolated in the Schwab adapter.

## Safety and request bounds

- The gateway remains GET-only.
- Option-chain output defaults to 40 and cannot exceed 100 contracts.
- If no dates are supplied to Schwab, only the next 45 days are requested.
- Every returned contract is filtered again locally against side, dates,
  strikes, and limit.
- Selected quote requests require between 1 and 100 symbols.
- A response larger than the configured byte limit is rejected.
- Raw provider responses are not exposed through MCP.

## Verification

Run:

```console
make check UV=.uv-bootstrap/bin/uv
```

The live Schwab check remains opt-in and user-controlled as documented in
`docs/MILESTONE_2.md`. No captured live response is required or permitted in
the committed fixture set.
