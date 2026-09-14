# Milestone 2 — Schwab OAuth and Read-Only Gateway

Completed in code: 2026-09-14

## Delivered

- Secret-safe Schwab configuration sourced from ignored local environment data.
- Authorization URL creation and constant-time state validation.
- Exact callback scheme, authority, and non-root path validation; equivalent
  empty and slash root paths are safely canonicalized.
- Authorization-code exchange and access-token refresh.
- Atomic token replacement with `0700` directory and `0600` file permissions on
  POSIX systems; token paths that are links or insecure files are rejected.
- Concurrency-safe refresh so simultaneous consumers share one token lifecycle.
- A GET-only HTTP gateway with timeouts, bounded retry, capped `Retry-After`, one
  forced refresh after HTTP 401, and stable error categories.
- A Schwab provider registered only when explicitly allow-listed.
- Generic `options_provider_auth_status` MCP tool.
- User-controlled local auth and opt-in live smoke-test commands.

The Schwab provider advertises no market-data capabilities in this milestone.
Those capabilities are activated only when Milestone 3 adds and tests canonical
response mapping.

## Security boundary

Credentials and tokens are never MCP arguments. Pydantic `SecretStr` protects
normal repr output, errors omit response bodies, callback input is hidden, and
the live smoke output contains only safe response-shape metadata. `.env` and
common token file patterns are ignored by Git.

## Local activation

1. Copy `.env.example` to `.env`.
2. Add `schwab` to `OPTIONS_ANALYSIS_ENABLED_PROVIDERS`.
3. Set the client ID, client secret, and the exact portal-registered callback.
4. Confirm the configured endpoint URLs against the current Schwab portal.
5. Run `uv run options-analysis-schwab-auth` and complete authorization yourself.
6. Set `OPTIONS_ANALYSIS_ALLOW_LIVE_SMOKE_TESTS=true` temporarily and run
   `uv run options-analysis-schwab-smoke --symbol SPY`.

Do not paste credentials, callback URLs, authorization codes, or tokens into a
chat, issue, log, test fixture, or commit.

## Verification

Offline tests cover URL generation, callback tampering, token response parsing,
redaction, refresh-token preservation, atomic private storage, symlink
rejection, 401 refresh, retry limits, rate-limit caps, entitlement errors,
schema errors, and the generic MCP tool over both in-memory and stdio protocol
connections.

The live OAuth and read are intentionally pending until the repository owner
performs the local activation steps. That operational check does not require a
code change.
