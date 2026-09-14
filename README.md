# Provider-Pluggable Options Analysis

This project will provide reusable, read-only market and brokerage data access
for applications that analyze stock-option positions. Charles Schwab is the
first provider adapter. MCP is the first delivery interface, not the core
architecture.

Provider portability is a primary design goal. Domain models, analytics,
application services, and MCP tool schemas remain provider-neutral. A new data
source should normally require only a provider plug-in, configuration, and
provider contract tests—not changes to analysis logic or MCP clients.

Repository: https://github.com/xuemingshen-oracle/options-analysis-mcp

## Current checkpoint

Milestone 2's code is complete. In addition to the offline skeleton, the project
has a Schwab adapter with OAuth callback validation, private atomic token
storage, refresh coordination, a GET-only HTTP gateway, typed provider errors,
and a third generic MCP tool, `options_provider_auth_status`. The live OAuth and
single-read check remain a local operational step requiring your approved
Schwab application.

Read these documents first:

- DESIGN.md — scope, architecture, models, tools, security, tests, and milestones.
- STATUS.md — durable checkpoint and instructions for continuing in another session.

## What works

- `options_server_info` returns safe runtime and read-only status.
- `options_list_providers` returns enabled providers and capabilities.
- `options_provider_auth_status` reports safe provider authorization state
  without exposing credentials or token values.
- The fake provider supplies deterministic quotes, expirations, chains, selected
  option quotes, and underlying history to offline services and contract tests.
- The MCP server runs locally over stdio.
- Provider-neutral models enforce instrument identity, timezone-aware data,
  Decimal values, provenance, namespaced extensions, and position invariants.

## Local setup and verification

Install `uv`, then run:

```console
uv sync --all-groups
make check
```

This workspace also has an ignored local `uv` bootstrap, so the same verification
can be run without a system installation:

```console
make check UV=.uv-bootstrap/bin/uv
```

Run the stdio server with:

```console
uv run options-analysis-mcp
```

The process waits for MCP messages on standard input and does not print a normal
interactive prompt.

## Schwab local authorization

Copy `.env.example` to the ignored `.env`, set the application client ID,
secret, and exact registered callback, and add `schwab` to
`OPTIONS_ANALYSIS_ENABLED_PROVIDERS`. Never commit `.env`.

Then run:

```console
uv run options-analysis-schwab-auth
```

The command opens the provider authorization page (unless `--no-open` is used)
and asks you to paste the full callback URL into hidden terminal input. Tokens
default to a user-only file under macOS Application Support, outside the repo.

To opt into one narrow read-only gateway check:

```console
OPTIONS_ANALYSIS_ALLOW_LIVE_SMOKE_TESTS=true \
  uv run options-analysis-schwab-smoke --symbol SPY
```

The smoke command reports only response shape metadata, not the quote payload.
The configured endpoint defaults must be confirmed against the current Schwab
developer portal during this first activation.

## Safety boundary

The planned initial system can read market data and, when a configured adapter
has appropriate read-only account access, positions. It will not place,
replace, or cancel orders.

Never commit an application secret, access token, refresh token, account number,
or captured Schwab response containing private account data.

## Resume

Read `STATUS.md` for the exact checkpoint. Milestone 3 adds normalized quote,
expiration, filtered-chain, option-quote, and underlying-history MCP tools while
preserving the provider-neutral interfaces.
