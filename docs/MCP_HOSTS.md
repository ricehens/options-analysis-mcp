# MCP Host Configuration

Build the environment first with `uv sync --all-groups`. Configure a local stdio
server in an MCP-compatible host using the equivalent of:

```json
{
  "mcpServers": {
    "options-analysis": {
      "command": "/Users/xuemingshen/Workspaces/schwab/.venv/bin/options-analysis-mcp",
      "args": [],
      "cwd": "/Users/xuemingshen/Workspaces/schwab"
    }
  }
}
```

Host configuration formats differ; translate the three fields without adding
shell quoting. Keeping the repository as `cwd` lets Pydantic settings find the
ignored `.env`. Do not copy Schwab credentials into the host configuration.

After restarting the host:

1. List tools and confirm all names begin with `options_`.
2. Call `options_server_info` and confirm `read_only` is true.
3. Call `options_list_providers`; start with `fake`.
4. Call `options_get_underlying_quote` for `SPY`.
5. Call `options_analyze_positions` with the README example.

Successful result objects contain their named data field and `error: null`.
Handled failures contain a non-null `error` with no provider body or secret.
Transport-level invalid arguments can still be reported by the MCP host itself.
