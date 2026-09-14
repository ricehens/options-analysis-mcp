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

The latest production UI is bundled with the Python package. Start the complete
local workspace with `make web-api` and open `http://127.0.0.1:8000`. The
browser uses the same configured default provider as MCP. The committed default
is `fake`, so this path works fully offline.

For frontend development, start `make web-api` and `make web-ui` in separate
terminals and open `http://127.0.0.1:5173`. Vite proxies `/api` to FastAPI.
After a UI change, run `make web-build`; this replaces the packaged assets under
`src/options_analysis/web/static`.

Use the **Text size** controls at the bottom of the desktop sidebar (or below
the watchlist on a narrow screen) to select 90%, 100%, 115%, or 130%. The middle
button resets to 100%. This preference is stored only in browser-local storage;
native browser zoom remains available independently.

The **Underlying history** panel requests one bounded view at a time. `1m`
shows one-minute bars over one day, `5m` covers one week, `1D` covers one year,
`1W` covers five years, and `1M` covers twenty years. The API returns at most
500 ordered bars. Availability and retention still depend on the selected
provider.

## 3. Enable Schwab

1. In the Schwab Developer Portal, select **Create App**.
2. Register `https://127.0.0.1` as the callback URL so it matches the project
   default. If you choose another callback, use the identical scheme, host,
   port, and path in local configuration.
3. Select **Market Data Production** for quotes, option chains, Greeks, and
   underlying history. Trader/account access is optional and is not required
   for caller-supplied position analysis.
4. Wait until the application is approved and shown as ready for use.
5. In the ignored `.env`, set the portal App Key as the client ID, the App
   Secret as the client secret, and the exact registered callback. Never place
   these values in chat, screenshots, logs, or Git.
6. Set `OPTIONS_ANALYSIS_ENABLED_PROVIDERS=["fake","schwab"]`.
7. Keep `fake` as the default until live validation is complete.
8. Run `uv run options-analysis-schwab-auth` in a private terminal.
9. Complete provider login yourself and paste the full callback into the hidden
   prompt.
10. Temporarily opt in and run
   `OPTIONS_ANALYSIS_ALLOW_LIVE_SMOKE_TESTS=true uv run options-analysis-schwab-smoke --symbol SPY`.
11. Validate mappings listed in `docs/MILESTONE_3.md`; do not save a live body.
12. Set `OPTIONS_ANALYSIS_DEFAULT_MARKET_DATA_PROVIDER=schwab` when satisfied.

Restart the HTTP API after changing provider configuration. The browser needs
no Schwab-specific setting and must never receive a client secret or token.

### Local workspace state

Watchlist changes persist at
`~/Library/Application Support/options-analysis-mcp/state.sqlite3`. Set
`OPTIONS_ANALYSIS_STATE_DB_PATH` to an absolute path to override it. To start
fresh, stop the API and move that one database file to Trash; the next watchlist
request creates a new database with `SPY`, `QQQ`, and `IWM`. Do not remove the
application-support directory recursively because it may also contain the
Schwab token file.

Named strategy drafts use a separate table in the same state database. Saving
the same name, ignoring case, updates that draft while preserving its ID and
creation time. A saved definition contains symbols, signed quantities, entry
prices, template identity, and the provider ID—not quote snapshots, tokens, or
orders. Opening a draft requests current quotes from its saved provider, so it
can fail visibly if that provider is disabled or needs reauthorization.

### Strategy analysis

Load a symbol with both calls and puts and a strike range wide enough for the
selected template. Choosing a template generates a draft using strikes near the
underlying mark; every action, quantity, and entry price remains editable.
Template entries default to current marks. Results are research calculations,
not executable quotes or order previews. Expand assumptions and warnings below
the scenario table before interpreting a result.

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
