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

Milestone 1 is complete and awaiting review. The offline skeleton includes
strict domain models, provider capability contracts, an allow-listed registry,
a deterministic fake provider, and two working MCP foundation tools. No Schwab
credentials, tokens, SDK calls, or network integration have been added.

Read these documents first:

- DESIGN.md — scope, architecture, models, tools, security, tests, and milestones.
- STATUS.md — durable checkpoint and instructions for continuing in another session.

## What works

- `options_server_info` returns safe runtime and read-only status.
- `options_list_providers` returns enabled providers and capabilities.
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

## Safety boundary

The planned initial system can read market data and, when a configured adapter
has appropriate read-only account access, positions. It will not place,
replace, or cancel orders.

Never commit an application secret, access token, refresh token, account number,
or captured Schwab response containing private account data.

## Resume

After reviewing the Milestone 1 skeleton and `STATUS.md`, explicitly approve
Milestone 2. That milestone adds Schwab OAuth, secure local token handling, the
read-only Schwab gateway, and provider authentication status. Work pauses again
after that checkpoint.
