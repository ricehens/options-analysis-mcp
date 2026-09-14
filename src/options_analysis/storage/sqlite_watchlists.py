"""Small SQLite adapter for the single-user local watchlist."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from options_analysis.domain import WatchlistItem


def default_state_db_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "options-analysis-mcp"
        / "state.sqlite3"
    )


class SQLiteWatchlistRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=5)
        if os.name == "posix":
            self._path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self, default_symbols: tuple[str, ...]) -> None:
        with self._connection() as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist_items (
                    symbol TEXT PRIMARY KEY COLLATE NOCASE,
                    created_at TEXT NOT NULL,
                    sort_order INTEGER NOT NULL UNIQUE CHECK (sort_order >= 0)
                )
                """
            )
            seeded = connection.execute(
                "SELECT value FROM app_metadata WHERE key = 'watchlist_seeded'"
            ).fetchone()
            if seeded is not None:
                return
            created_at = datetime.now(UTC).isoformat()
            connection.executemany(
                """
                INSERT OR IGNORE INTO watchlist_items
                    (symbol, created_at, sort_order)
                VALUES (?, ?, ?)
                """,
                (
                    (symbol, created_at, sort_order)
                    for sort_order, symbol in enumerate(default_symbols)
                ),
            )
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES ('watchlist_seeded', '1')"
            )

    def list_items(self) -> tuple[WatchlistItem, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT symbol, created_at, sort_order
                FROM watchlist_items
                ORDER BY sort_order, symbol
                """
            ).fetchall()
        return tuple(
            WatchlistItem(
                symbol=str(row["symbol"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
                sort_order=int(row["sort_order"]),
            )
            for row in rows
        )

    def add(self, symbol: str) -> WatchlistItem:
        with self._connection() as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT symbol, created_at, sort_order
                FROM watchlist_items
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
            if existing is not None:
                return self._item(existing)
            row = connection.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM watchlist_items"
            ).fetchone()
            assert row is not None
            sort_order = int(row[0])
            created_at = datetime.now(UTC)
            connection.execute(
                """
                INSERT INTO watchlist_items (symbol, created_at, sort_order)
                VALUES (?, ?, ?)
                """,
                (symbol, created_at.isoformat(), sort_order),
            )
        return WatchlistItem(
            symbol=symbol, created_at=created_at, sort_order=sort_order
        )

    def remove(self, symbol: str) -> bool:
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM watchlist_items WHERE symbol = ?", (symbol,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def _item(row: sqlite3.Row) -> WatchlistItem:
        return WatchlistItem(
            symbol=str(row["symbol"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            sort_order=int(row["sort_order"]),
        )
