# Milestone 6B — Persistent Watchlists

Completed in code: 2026-09-14

## Delivered

- A provider-neutral `WatchlistService` behind a small repository protocol.
- A SQLite repository that initializes lazily outside the source tree.
- First-use defaults (`SPY`, `QQQ`, and `IWM`) that are seeded exactly once.
- Idempotent symbol addition, removal, stable ordering, and preservation of an
  intentionally empty watchlist across process restarts.
- `GET`, `POST`, and `DELETE` endpoints under `/api/v1/watchlist`.
- React controls backed by those endpoints rather than component-only state.
- A canonical root `TODO.md` with stable work IDs for cross-session progress.

## Storage and boundary decisions

- Persistence is an infrastructure adapter; the domain service does not import
  SQLite or provider code.
- The default database is
  `~/Library/Application Support/options-analysis-mcp/state.sqlite3`.
- The database path may be overridden only with an absolute path.
- Parent directories and database permissions are user-only on POSIX systems.
- Watchlist writes mutate local preferences only. Broker and market-data
  interfaces remain read-only, and no order capability is introduced.
- Database initialization is lazy, so starting MCP without using watchlists does
  not create a state file.

## HTTP contract

- `GET /api/v1/watchlist` returns ordered items.
- `POST /api/v1/watchlist` accepts `{ "symbol": "AAPL" }`, normalizes the
  symbol, and returns the full list.
- `DELETE /api/v1/watchlist/{symbol}` is idempotent and returns the full list.

Symbols must start with a letter and contain no more than 12 letters, numbers,
dots, or hyphens.

## Verification

- SQLite tests cover one-time seeding, private file mode, empty-list restart
  behavior, idempotent normalized additions, removals, and invalid input.
- HTTP tests cover the complete CRUD contract.
- A live local GET/POST/DELETE sequence succeeded through the Vite proxy using
  a temporary database.
- The final release check includes Python format/lint/type/tests, React
  TypeScript/Vite build, and Python source/wheel packaging.

## Next milestone

Milestone 6C implements the richer option-chain explorer described by `UI-020`
through `UI-022` in `TODO.md`.
