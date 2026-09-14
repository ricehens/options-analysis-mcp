"""SQLite adapter for named, provider-scoped strategy drafts."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from options_analysis.domain import (
    StrategyDraft,
    StrategyDraftDefinition,
    StrategyDraftLeg,
)


class SQLiteStrategyDraftRepository:
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

    def initialize(self) -> None:
        with self._connection() as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_drafts (
                    draft_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    underlying_symbol TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    strategy_template_id TEXT,
                    legs_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def list_drafts(self) -> tuple[StrategyDraft, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT draft_id, name, underlying_symbol, provider_id,
                       strategy_template_id, legs_json, created_at, updated_at
                FROM strategy_drafts
                ORDER BY updated_at DESC, name COLLATE NOCASE
                """
            ).fetchall()
        return tuple(self._draft(row) for row in rows)

    def save(self, definition: StrategyDraftDefinition) -> StrategyDraft:
        now = datetime.now(UTC)
        legs_json = json.dumps(
            [leg.model_dump(mode="json") for leg in definition.legs],
            separators=(",", ":"),
        )
        with self._connection() as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT draft_id, created_at
                FROM strategy_drafts
                WHERE name = ? COLLATE NOCASE
                """,
                (definition.name,),
            ).fetchone()
            draft_id = (
                UUID(str(existing["draft_id"])) if existing is not None else uuid4()
            )
            created_at = (
                datetime.fromisoformat(str(existing["created_at"]))
                if existing is not None
                else now
            )
            connection.execute(
                """
                INSERT INTO strategy_drafts (
                    draft_id, name, underlying_symbol, provider_id,
                    strategy_template_id, legs_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    name = excluded.name,
                    underlying_symbol = excluded.underlying_symbol,
                    provider_id = excluded.provider_id,
                    strategy_template_id = excluded.strategy_template_id,
                    legs_json = excluded.legs_json,
                    updated_at = excluded.updated_at
                """,
                (
                    str(draft_id),
                    definition.name,
                    definition.underlying_symbol,
                    definition.provider_id,
                    definition.strategy_template_id,
                    legs_json,
                    created_at.isoformat(),
                    now.isoformat(),
                ),
            )
        return StrategyDraft(
            **definition.model_dump(),
            draft_id=draft_id,
            created_at=created_at,
            updated_at=now,
        )

    def remove(self, draft_id: UUID) -> bool:
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM strategy_drafts WHERE draft_id = ?", (str(draft_id),)
            )
            return cursor.rowcount > 0

    @staticmethod
    def _draft(row: sqlite3.Row) -> StrategyDraft:
        raw_legs = json.loads(str(row["legs_json"]))
        return StrategyDraft(
            draft_id=UUID(str(row["draft_id"])),
            name=str(row["name"]),
            underlying_symbol=str(row["underlying_symbol"]),
            provider_id=str(row["provider_id"]),
            strategy_template_id=(
                str(row["strategy_template_id"])
                if row["strategy_template_id"] is not None
                else None
            ),
            legs=tuple(StrategyDraftLeg.model_validate(item) for item in raw_legs),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
