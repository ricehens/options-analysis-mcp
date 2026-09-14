"""Watchlist use cases independent of storage and market-data providers."""

from typing import Protocol

from options_analysis.domain.watchlists import (
    WatchlistItem,
    normalize_watchlist_symbol,
)


class WatchlistRepository(Protocol):
    def initialize(self, default_symbols: tuple[str, ...]) -> None: ...

    def list_items(self) -> tuple[WatchlistItem, ...]: ...

    def add(self, symbol: str) -> WatchlistItem: ...

    def remove(self, symbol: str) -> bool: ...


class WatchlistService:
    def __init__(
        self,
        repository: WatchlistRepository,
        *,
        default_symbols: tuple[str, ...] = ("SPY", "QQQ", "IWM"),
    ) -> None:
        self._repository = repository
        self._default_symbols = tuple(
            normalize_watchlist_symbol(symbol) for symbol in default_symbols
        )

    def list_items(self) -> tuple[WatchlistItem, ...]:
        self._repository.initialize(self._default_symbols)
        return self._repository.list_items()

    def add(self, symbol: str) -> tuple[WatchlistItem, ...]:
        self._repository.initialize(self._default_symbols)
        self._repository.add(normalize_watchlist_symbol(symbol))
        return self._repository.list_items()

    def remove(self, symbol: str) -> tuple[WatchlistItem, ...]:
        self._repository.initialize(self._default_symbols)
        self._repository.remove(normalize_watchlist_symbol(symbol))
        return self._repository.list_items()
