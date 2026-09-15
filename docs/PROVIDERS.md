# Provider Plug-in Guide

## Boundary

A provider adapter may depend on canonical models and provider contracts. The
domain, analytics, services, and MCP layers must never import that adapter.
Equivalent providers must not require changes to existing MCP tool names or
analysis logic.

Implement `Provider` plus only the capability protocols you advertise:

- `MarketDataProvider`
- `HistoricalDataProvider`
- `PortfolioProvider`
- `StreamingProvider` (deferred)
- `AuthenticatingProvider` when authentication applies

There is intentionally no execution provider.

Technical indicators are not provider capabilities. Adapters return canonical
price bars; `TechnicalIndicatorService` then runs registered calculators over
those bars. Adding SMA, EMA, Bollinger Bands, RSI, or another derived indicator
must not require a Schwab, replay, or future-provider adapter change. A source's
proprietary signal may instead be preserved as a namespaced extension or modeled
as a separately documented capability when it cannot be reproduced locally.

## Registration

Expose a zero-argument factory through the entry-point group:

```toml
[project.entry-points."options_analysis.providers"]
tradier = "my_tradier_adapter:create_provider"
```

The descriptor ID and entry-point name must match. Installation alone does not
activate code: add the same ID to `OPTIONS_ANALYSIS_ENABLED_PROVIDERS`. The
registry skips disabled entry points without importing them.

## Built-in replay adapter

`replay` implements the market-data and underlying-history contracts over an
immutable local JSON bundle. It is useful for UI demonstrations, deterministic
bug reproduction, contract development, and later authorized/sanitized data
captures. It performs no network or authentication operation.

The bundle schema is owned by `ReplayBundle` and begins at `schema_version: 1`.
It records source label/provider/time/usage notes plus one or more canonical
symbol snapshots. Loaded quotes are routed under provider ID `replay`; the
original provider ID stays in field provenance and
`replay.original_provider_id`.

Configure only an absolute local path. The loader applies a 25 MB default bound,
strict nested-model validation, unique identifiers, and ordered timestamps. It
does not watch or mutate the file. Real data remains subject to its source terms
and should normally stay outside Git.

## Canonical mapping requirements

- Use `Decimal` at API boundaries for prices, strikes, quantities, and Greeks.
- Use timezone-aware timestamps and distinguish source time from receipt time.
- Preserve provider and field provenance.
- Put useful noncanonical fields under namespaced extension keys such as
  `tradier.greeks_source`.
- Emit quality warnings; never silently replace questionable upstream values.
- Preserve provider symbol and canonical OCC symbol separately.
- Keep authentication and raw response models inside the adapter package.
- Map errors to the stable provider exception classes without including bodies.

## Conformance

The reusable helper ships in the installed package:

```python
from options_analysis.testing import assert_market_data_provider_contract


async def test_adapter_contract(configured_provider):
    await assert_market_data_provider_contract(configured_provider)
```

Use synthetic fixtures for normal, partial, empty, rate-limited, authorization,
and schema-drift cases. A live test must be opt-in, narrow, read-only, and must
not write its response to disk.

## Review checklist

- Only declared capabilities are advertised.
- Every capability has contract and adapter tests.
- Requests and output are bounded.
- Retry applies only to safe transient reads.
- Secrets never enter model-visible inputs or output.
- Adding the adapter changes composition/configuration only, not analysis.
