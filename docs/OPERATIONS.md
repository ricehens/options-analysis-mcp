# Local Operations Guide

## 1. Install and verify

Requirements: Python 3.12 or newer and `uv`.

```console
cd /Users/xuemingshen/Workspaces/schwab
uv sync --all-groups
make check
```

The existing workspace bootstrap can be used with
`make check UV=.uv-bootstrap/bin/uv`.

## 2. Offline mode

The committed `.env.example` enables only `fake`. Copy it to the ignored `.env`
if you want local overrides. Run `uv run options-analysis-mcp`; a stdio MCP
server waits silently for protocol messages.

Use the fake provider first to validate the host and these tools:

- `options_server_info`
- `options_list_providers`
- `options_get_option_chain` with `SPY` and a small limit
- `options_analyze_positions` with the example in `README.md`

### Browser workspace

Install the locked frontend dependencies once:

```console
make web-sync
```

Then start `make web-api` and `make web-ui` in separate terminals and open
`http://127.0.0.1:5173`. The browser uses the same configured default provider
as MCP. The committed default is `fake`, so this path works fully offline after
dependencies are installed.

## 3. Enable Schwab

1. Confirm the developer application is approved and its callback URI.
2. In the ignored `.env`, set client ID, client secret, and the exact callback.
3. Set `OPTIONS_ANALYSIS_ENABLED_PROVIDERS=["fake","schwab"]`.
4. Keep `fake` as the default until live validation is complete.
5. Run `uv run options-analysis-schwab-auth` in a private terminal.
6. Complete provider login yourself and paste the full callback into the hidden
   prompt.
7. Temporarily opt in and run
   `OPTIONS_ANALYSIS_ALLOW_LIVE_SMOKE_TESTS=true uv run options-analysis-schwab-smoke --symbol SPY`.
8. Validate mappings listed in `docs/MILESTONE_3.md`; do not save a live body.
9. Set `OPTIONS_ANALYSIS_DEFAULT_MARKET_DATA_PROVIDER=schwab` when satisfied.

Restart the HTTP API after changing provider configuration. The browser needs
no Schwab-specific setting and must never receive a client secret or token.

## 4. Routine checks

- Call `options_provider_auth_status` before a live session.
- `refresh_needed` is handled automatically on the next request.
- `reauthorization_required` means rerun the local authorization helper.
- An MCP error object reports category, retryability, reauthorization need, and
  sanitized schema field paths.
- The one-second underlying-quote cache can be disabled with
  `OPTIONS_ANALYSIS_SNAPSHOT_CACHE_TTL_SECONDS=0`.

## 5. Troubleshooting

| Symptom | Action |
| --- | --- |
| `configuration` | Check enabled provider, ignored `.env`, exact variable names, and working directory. |
| `authorization` | Call auth status; rerun the local helper if requested. |
| `entitlement` | Confirm Market Data Production or Trader API access in the portal. |
| `rate_limit` | Respect `retryable`; reduce polling and chain breadth. |
| `upstream_schema` | Record only category and `field_paths`; compare official docs and update the adapter/fixture synthetically. |
| Empty or partial chain | Narrow dates/strikes, inspect warnings, and verify market/session status. |
| MCP process exits | Run `make check`, then start the command in a terminal without sending non-MCP input. |

## 6. Token removal

The default macOS token is
`~/Library/Application Support/options-analysis-mcp/schwab-token.json`. Stop the
server before moving that one file to Trash. Reauthorization creates a new one.
Never use a recursive deletion command for token cleanup.
