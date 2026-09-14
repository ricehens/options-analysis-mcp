# Provider-Pluggable Options Analysis

This project will provide reusable, read-only market and brokerage data access
for applications that analyze stock-option positions. Charles Schwab is the
first provider adapter. MCP is the first delivery interface, not the core
architecture.

Provider portability is a primary design goal. Domain models, analytics,
application services, MCP tool schemas, and HTTP endpoints remain
provider-neutral. A new data source should normally require only a provider
plug-in, configuration, and provider contract tests—not changes to analysis
logic or clients.

Repository: https://github.com/xuemingshen-oracle/options-analysis-mcp

## Current checkpoint

Milestone 6C is complete. A responsive React workspace and local-only FastAPI
facade sit beside the MCP server and reuse the same provider-neutral services.
The UI provides a persistent SQLite-backed watchlist, selected-symbol quote
summary, a sortable and filterable detailed option chain, and contract
selection into editable draft legs. Live Schwab activation remains a local step
requiring your developer application.

Read these documents first:

- DESIGN.md — scope, architecture, models, tools, security, tests, and milestones.
- STATUS.md — durable checkpoint and instructions for continuing in another session.
- TODO.md — canonical cross-session backlog with stable task IDs and dependencies.

## What works

- `options_server_info` returns safe runtime and read-only status.
- `options_list_providers` returns enabled providers and capabilities.
- `options_provider_auth_status` reports safe provider authorization state
  without exposing credentials or token values.
- `options_get_underlying_quote` returns a normalized quote with provenance and
  quality warnings.
- `options_get_option_expirations` lists available expiration dates and DTE.
- `options_get_option_chain` returns at most 100 locally re-filtered contracts;
  its default is 40 contracts and a 45-day Schwab request window.
- `options_get_option_quotes` retrieves 1–100 explicitly selected contracts.
- `options_get_price_history` retrieves underlying bars, not historical option
  chains.
- `options_analyze_positions` analyzes 1–100 signed equity, ETF, or option legs.
  Positive quantity is long and negative quantity is short.
- The fake provider supplies deterministic quotes, expirations, chains, selected
  option quotes, and underlying history to offline services and contract tests.
- The MCP server runs locally over stdio.
- The HTTP API runs locally on `127.0.0.1:8000` and publishes OpenAPI at
  `/api/docs`.
- The React UI runs on `127.0.0.1:5173` and proxies `/api` to the local API.
- Watchlist add/remove changes persist in a private local SQLite database.
- The option chain supports expiration/side/strike, near-money,
  open-interest, and maximum bid/ask-spread filters.
- Calls and puts show delta, IV, bid, ask, spread, open interest, moneyness,
  freshness, and warning counts.
- Selected contracts form an editable buy/sell draft; strategy calculations
  follow in Milestone 6D.
- Provider-neutral models enforce instrument identity, timezone-aware data,
  Decimal values, provenance, namespaced extensions, and position invariants.

Example position-analysis arguments:

```json
{
  "legs": [
    {
      "symbol": "SPY300118C00095000",
      "asset_type": "option",
      "quantity": "1",
      "average_open_price": "6"
    },
    {
      "symbol": "SPY300118C00100000",
      "asset_type": "option",
      "quantity": "-1",
      "average_open_price": "3"
    }
  ],
  "valuation_mode": "mark",
  "scenario_moves": ["-0.10", "0", "0.10"]
}
```

Option prices and Greeks are treated as per underlying unit and multiplied by
the contract multiplier. `max_loss` is the minimum profit/loss value, so a loss
is represented as a negative number. Delta-gamma scenarios hold volatility and
time constant; they are local approximations, not forecasts.

Handled tool failures return a non-null `error` object with a stable category,
retryability, reauthorization flag, and sanitized schema field paths. Successful
tool results have `error: null`.

## Local setup and verification

Install `uv`, then run:

```console
uv sync --all-groups
make check
make web-sync
make web-build
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

## Browser UI

Start the local API and UI in two terminals:

```console
make web-api
make web-ui
```

Open `http://127.0.0.1:5173`. The committed default uses deterministic fake
data, requires no credentials, and makes no external font or data request. The
API binds only to loopback and accepts development cross-origin reads only from
the two local Vite origins.

The watchlist database defaults to
`~/Library/Application Support/options-analysis-mcp/state.sqlite3`. Override it
with the absolute `OPTIONS_ANALYSIS_STATE_DB_PATH` setting when needed.

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

## Documentation

- `docs/OPERATIONS.md` — setup, authorization, routine use, and troubleshooting.
- `SECURITY.md` — threat boundary, secret handling, and incident response.
- `docs/MCP_HOSTS.md` — generic local stdio host configuration.
- `docs/PROVIDERS.md` — adapter API, entry points, mapping rules, and conformance.
- `docs/RELEASE.md` — quality, build, version, Git, and tag checklist.
- `docs/MILESTONE_6A.md` — browser foundation contract and next UI work.
- `docs/MILESTONE_6B.md` — persistent watchlist design and verification.
- `docs/MILESTONE_6C.md` — chain exploration and contract-selection contract.
- `docs/MILESTONE_*.md` — durable implementation and verification decisions.
- `TODO.md` — ordered durable work queue for this and future sessions.

## Resume

Read `STATUS.md` for the exact checkpoint. Streaming remains optional and should
be added only after live use demonstrates that bounded snapshot reads are too
slow for the analysis workflow.
