import os
from pathlib import Path

from options_analysis.services import WatchlistService
from options_analysis.storage import SQLiteWatchlistRepository


def service(path: Path) -> WatchlistService:
    return WatchlistService(SQLiteWatchlistRepository(path))


def test_first_use_seeds_once_and_preserves_an_empty_watchlist(tmp_path: Path) -> None:
    database = tmp_path / "nested" / "state.sqlite3"
    watchlist = service(database)

    assert [item.symbol for item in watchlist.list_items()] == ["SPY", "QQQ", "IWM"]
    if os.name == "posix":
        assert database.stat().st_mode & 0o777 == 0o600
    watchlist.remove("SPY")
    watchlist.remove("QQQ")
    watchlist.remove("IWM")

    restarted = service(database)
    assert restarted.list_items() == ()


def test_add_normalizes_and_is_idempotent_across_service_instances(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    watchlist = service(database)

    watchlist.add(" aapl ")
    watchlist.add("AAPL")

    restarted = service(database)
    assert [item.symbol for item in restarted.list_items()] == [
        "SPY",
        "QQQ",
        "IWM",
        "AAPL",
    ]


def test_invalid_symbol_is_rejected_without_changing_storage(tmp_path: Path) -> None:
    watchlist = service(tmp_path / "state.sqlite3")

    try:
        watchlist.add("SPY; DROP TABLE")
    except ValueError as error:
        assert "symbol must start with a letter" in str(error)
    else:
        raise AssertionError("invalid symbol should be rejected")

    assert [item.symbol for item in watchlist.list_items()] == ["SPY", "QQQ", "IWM"]
