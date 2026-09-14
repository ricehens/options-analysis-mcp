# Milestone 5 — Hardening and Packaging

Completed in code: 2026-09-14

## Delivered

- Stable MCP error details for configuration, authorization, entitlement,
  not-found, unsupported capability, validation, rate limit, upstream
  availability, and upstream schema failures.
- Successful and handled-error outputs retain one object schema per tool;
  `error` is null on success and populated on handled failure.
- Schema drift exposes at most five Pydantic field paths and never copies an
  upstream body into the error.
- A bounded process-local LRU/TTL cache for repeated underlying snapshots. The
  default is one second and 512 entries; TTL zero disables it.
- The provider market-data conformance helper is included in the package under
  `options_analysis.testing`.
- `SECURITY.md`, operations, MCP host, plug-in, and release guides.
- `CHANGELOG.md` and a `make release-check` command that runs all checks and
  builds source/wheel distributions.

## Error contract

Tool callers should first inspect `error`. Important fields are:

- `category`
- `message`
- `retryable`
- `reauthorization_required`
- `field_paths`

MCP argument-schema failures can still be emitted by the MCP implementation
before a tool function runs. All provider and service errors reached by a tool
are converted to the stable object.

## Cache contract

Only underlying quotes are cached. The key contains actual provider ID and
normalized symbol. Entries expire monotonically, access refreshes LRU order,
and insertion evicts beyond the configured maximum. Chains, selected option
quotes, position results, credentials, and failures are not cached.

## Verification

Tests cover stable MCP error serialization, cache TTL/LRU/disabled behavior,
and sanitized schema paths in addition to all previous provider, gateway,
market-data, and analytics checks. `make release-check` must pass before the
checkpoint is tagged.
